from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import db

app = FastAPI(title="Test 3 — Movie Search")


@app.get("/api/health")
def health():
    return {"status": "ok", "experiment": "test3-search"}


@app.get("/api/filters")
def get_filters():
    return {"genres": db.get_genres(), "directors": db.get_directors()}


@app.get("/api/movies")
def browse(genre: str | None = None, director: str | None = None,
           year: int | None = None, sort: str = "rating", limit: int = 50, offset: int = 0):
    movies, total = db.browse_movies(genre=genre, director=director, year=year, sort=sort, limit=limit, offset=offset)
    return {"movies": movies, "total": total}


@app.get("/api/search")
def search(q: str, mode: str = "title"):
    if not q.strip():
        return {"results": []}
    results = db.search_movies(q.strip(), mode=mode)
    return {"results": results, "count": len(results)}


@app.get("/api/movies/{movie_id}")
def get_movie(movie_id: int):
    movie = db.get_movie(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


# Serve UI — must be last
ui_path = Path(__file__).parent.parent / "ui"
app.mount("/", StaticFiles(directory=str(ui_path), html=True), name="ui")
