"""Generate fake movie data and ingest into SQLite with FTS5 indexes."""

import sqlite3
import json
import random
from pathlib import Path

DB_PATH = Path(__file__).parent / "movies.db"

GENRES = ["Action", "Comedy", "Drama", "Sci-Fi", "Horror", "Thriller", "Romance", "Documentary", "Animation", "Fantasy"]
DIRECTORS = [
    "Sofia Chen", "Marcus Williams", "Aiko Tanaka", "James Rodriguez", "Elena Popov",
    "David Kim", "Sarah Mitchell", "Omar Hassan", "Lisa Park", "Carlos Mendez",
    "Nina Johansson", "Alex Turner", "Priya Sharma", "Michael O'Brien", "Fatima Al-Rashid",
]
ACTORS = [
    "Emma Stone", "Ryan Chen", "Zoe Martinez", "Leo Park", "Ana Williams",
    "Sam Rodriguez", "Maya Johnson", "Tom Hassan", "Olivia Kim", "Jack Turner",
    "Grace Lee", "Noah Mitchell", "Lily Tanaka", "Ethan Brown", "Chloe Davis",
    "Aiden Wilson", "Mia Sharma", "Lucas Garcia", "Sophia Anderson", "Owen Taylor",
]
ADJECTIVES = ["The Last", "Dark", "Eternal", "Hidden", "Silent", "Broken", "Lost", "Rising", "Fallen", "Crimson"]
NOUNS = ["Kingdom", "Shadow", "Code", "Protocol", "Signal", "Horizon", "Legacy", "Cipher", "Frontier", "Paradox"]
VERBS = ["Returns", "Awakens", "Rises", "Falls", "Strikes", "Begins", "Ends", "Continues", "Unfolds", "Collides"]

def gen_title():
    pattern = random.choice([
        lambda: f"{random.choice(ADJECTIVES)} {random.choice(NOUNS)}",
        lambda: f"The {random.choice(NOUNS)} {random.choice(VERBS)}",
        lambda: f"{random.choice(NOUNS)}: {random.choice(ADJECTIVES)} {random.choice(NOUNS)}",
        lambda: f"{random.choice(ADJECTIVES)} {random.choice(NOUNS)} {random.choice(['II', 'III', '2', '3'])}",
    ])
    return pattern()

def gen_synopsis(title, genre):
    templates = [
        f"In this gripping {genre.lower()} film, a group of unlikely heroes must navigate a world where {random.choice(['nothing is as it seems', 'danger lurks around every corner', 'time itself is running out'])}. {title} takes viewers on a journey through {random.choice(['a dystopian future', 'the streets of neo-Tokyo', 'a war-torn landscape', 'the depths of space', 'a forgotten kingdom'])}.",
        f"When {random.choice(['a mysterious artifact', 'an ancient prophecy', 'a coded message', 'a secret organization'])} threatens to {random.choice(['destroy everything', 'change the course of history', 'unravel reality itself'])}, one person must {random.choice(['rise to the challenge', 'confront their past', 'make the ultimate sacrifice'])}. A {genre.lower()} that {random.choice(['redefines the genre', 'keeps you on the edge of your seat', 'will leave you breathless'])}.",
        f"{title} follows {random.choice(['a retired detective', 'a young scientist', 'a rebel leader', 'an ordinary teacher', 'a disgraced pilot'])} who discovers {random.choice(['a hidden truth', 'a parallel dimension', 'a conspiracy reaching the highest levels', 'an alien signal'])}. This {genre.lower()} masterpiece explores themes of {random.choice(['identity and belonging', 'power and corruption', 'love and sacrifice', 'technology and humanity'])}.",
    ]
    return random.choice(templates)

def gen_review(title):
    templates = [
        f"A masterful blend of storytelling and visual artistry. {title} delivers on every promise.",
        f"While the first act drags slightly, the payoff in the final hour is extraordinary. Worth watching twice.",
        f"The performances elevate what could have been a formulaic plot into something genuinely moving.",
        f"Bold, ambitious, and occasionally messy — but never boring. {title} swings for the fences.",
        f"A technical marvel with heart. The score alone is worth the price of admission.",
        f"Disappointing follow-up that fails to capture the magic of its premise. Beautiful to look at, though.",
        f"One of the year's best surprises. Went in with low expectations, came out completely blown away.",
        f"Smart, funny, and surprisingly emotional. {title} proves that blockbusters can also be art.",
    ]
    return random.choice(templates)

def generate_movies(n=200):
    movies = []
    used_titles = set()
    for i in range(n):
        title = gen_title()
        while title in used_titles:
            title = gen_title()
        used_titles.add(title)

        genre = random.choice(GENRES)
        year = random.randint(2015, 2026)
        rating = round(random.uniform(4.0, 9.5), 1)
        director = random.choice(DIRECTORS)
        cast = random.sample(ACTORS, k=random.randint(2, 5))
        synopsis = gen_synopsis(title, genre)
        reviews = [gen_review(title) for _ in range(random.randint(1, 3))]
        budget_m = random.choice([5, 10, 15, 25, 50, 75, 100, 150, 200])
        runtime = random.randint(85, 180)

        movies.append({
            "id": i + 1,
            "title": title,
            "year": year,
            "genre": genre,
            "director": director,
            "cast": cast,
            "rating": rating,
            "synopsis": synopsis,
            "reviews": reviews,
            "budget_millions": budget_m,
            "runtime_minutes": runtime,
        })
    return movies

def create_db(movies):
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")

    conn.executescript("""
        CREATE TABLE movies (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            year INTEGER NOT NULL,
            genre TEXT NOT NULL,
            director TEXT NOT NULL,
            cast_list TEXT NOT NULL,
            rating REAL NOT NULL,
            synopsis TEXT NOT NULL,
            budget_millions INTEGER,
            runtime_minutes INTEGER
        );

        CREATE TABLE reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER NOT NULL REFERENCES movies(id),
            text TEXT NOT NULL
        );

        CREATE VIRTUAL TABLE movies_fts USING fts5(
            title, director, cast_list, synopsis,
            content='movies',
            content_rowid='id'
        );

        CREATE VIRTUAL TABLE reviews_fts USING fts5(
            text,
            content='reviews',
            content_rowid='id'
        );
    """)

    for m in movies:
        conn.execute(
            "INSERT INTO movies (id, title, year, genre, director, cast_list, rating, synopsis, budget_millions, runtime_minutes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (m["id"], m["title"], m["year"], m["genre"], m["director"], ", ".join(m["cast"]), m["rating"], m["synopsis"], m["budget_millions"], m["runtime_minutes"]),
        )
        conn.execute(
            "INSERT INTO movies_fts (rowid, title, director, cast_list, synopsis) VALUES (?, ?, ?, ?, ?)",
            (m["id"], m["title"], m["director"], ", ".join(m["cast"]), m["synopsis"]),
        )
        for review in m["reviews"]:
            cur = conn.execute("INSERT INTO reviews (movie_id, text) VALUES (?, ?)", (m["id"], review))
            conn.execute("INSERT INTO reviews_fts (rowid, text) VALUES (?, ?)", (cur.lastrowid, review))

    conn.commit()

    # Verify
    count = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    review_count = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    print(f"Created {count} movies with {review_count} reviews in {DB_PATH}")
    conn.close()

if __name__ == "__main__":
    movies = generate_movies(200)
    create_db(movies)

    # Also save as JSON for reference
    json_path = Path(__file__).parent / "movies.json"
    with open(json_path, "w") as f:
        json.dump(movies, f, indent=2)
    print(f"Saved JSON to {json_path}")
