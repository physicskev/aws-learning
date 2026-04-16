import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "db" / "movies.db"


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def get_genres():
    conn = get_conn()
    rows = conn.execute("SELECT DISTINCT genre FROM movies ORDER BY genre").fetchall()
    conn.close()
    return [r["genre"] for r in rows]


def get_directors():
    conn = get_conn()
    rows = conn.execute("SELECT DISTINCT director FROM movies ORDER BY director").fetchall()
    conn.close()
    return [r["director"] for r in rows]


def browse_movies(genre: str | None = None, director: str | None = None,
                  year: int | None = None, sort: str = "rating", limit: int = 50, offset: int = 0):
    conn = get_conn()
    query = "SELECT * FROM movies WHERE 1=1"
    params = []
    if genre:
        query += " AND genre = ?"
        params.append(genre)
    if director:
        query += " AND director = ?"
        params.append(director)
    if year:
        query += " AND year = ?"
        params.append(year)

    if sort == "rating":
        query += " ORDER BY rating DESC"
    elif sort == "year":
        query += " ORDER BY year DESC"
    elif sort == "title":
        query += " ORDER BY title ASC"

    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    total = conn.execute(
        query.split("ORDER BY")[0].replace("SELECT *", "SELECT COUNT(*)"),
        params[:-2],
    ).fetchone()[0]
    conn.close()
    return [dict(r) for r in rows], total


def search_movies(q: str, mode: str = "title"):
    """Search using FTS5. mode='title' searches movies_fts, mode='review' searches reviews_fts."""
    conn = get_conn()

    if mode == "review":
        # Search reviews, return parent movies with snippets
        rows = conn.execute("""
            SELECT r.movie_id, snippet(reviews_fts, 0, '<mark>', '</mark>', '...', 40) as snippet,
                   r.id as review_id
            FROM reviews_fts
            JOIN reviews r ON reviews_fts.rowid = r.id
            WHERE reviews_fts MATCH ?
            ORDER BY rank
            LIMIT 50
        """, (q,)).fetchall()

        # Group by movie and fetch movie details
        movie_ids = list(set(r["movie_id"] for r in rows))
        if not movie_ids:
            # Fallback to LIKE
            rows = conn.execute("""
                SELECT r.movie_id, r.text as snippet, r.id as review_id
                FROM reviews r WHERE r.text LIKE ?
                LIMIT 50
            """, (f"%{q}%",)).fetchall()
            movie_ids = list(set(r["movie_id"] for r in rows))

        if not movie_ids:
            conn.close()
            return []

        placeholders = ",".join("?" * len(movie_ids))
        movies = conn.execute(f"SELECT * FROM movies WHERE id IN ({placeholders})", movie_ids).fetchall()
        movies_dict = {m["id"]: dict(m) for m in movies}

        results = []
        for mid in movie_ids:
            if mid in movies_dict:
                movie = movies_dict[mid]
                movie["matched_reviews"] = [
                    {"snippet": r["snippet"]} for r in rows if r["movie_id"] == mid
                ]
                results.append(movie)
        conn.close()
        return results

    else:
        # Search title/director/cast/synopsis
        rows = conn.execute("""
            SELECT movies_fts.rowid,
                   snippet(movies_fts, 0, '<mark>', '</mark>', '...', 20) as title_snippet,
                   snippet(movies_fts, 3, '<mark>', '</mark>', '...', 40) as synopsis_snippet
            FROM movies_fts
            WHERE movies_fts MATCH ?
            ORDER BY rank
            LIMIT 50
        """, (q,)).fetchall()

        if not rows:
            # FTS5 fallback to LIKE for special chars
            rows = conn.execute("""
                SELECT id as rowid, title as title_snippet, synopsis as synopsis_snippet
                FROM movies
                WHERE title LIKE ? OR director LIKE ? OR cast_list LIKE ? OR synopsis LIKE ?
                LIMIT 50
            """, (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()

        ids = [r["rowid"] for r in rows]
        if not ids:
            conn.close()
            return []

        snippets = {r["rowid"]: {"title_snippet": r["title_snippet"], "synopsis_snippet": r["synopsis_snippet"]} for r in rows}

        placeholders = ",".join("?" * len(ids))
        movies = conn.execute(f"SELECT * FROM movies WHERE id IN ({placeholders})", ids).fetchall()
        results = []
        for m in movies:
            movie = dict(m)
            s = snippets.get(m["id"], {})
            movie["title_snippet"] = s.get("title_snippet", m["title"])
            movie["synopsis_snippet"] = s.get("synopsis_snippet", "")
            results.append(movie)

        conn.close()
        return results


def get_movie(movie_id: int):
    conn = get_conn()
    movie = conn.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()
    if not movie:
        conn.close()
        return None
    result = dict(movie)
    reviews = conn.execute("SELECT * FROM reviews WHERE movie_id = ?", (movie_id,)).fetchall()
    result["reviews"] = [dict(r) for r in reviews]
    conn.close()
    return result
