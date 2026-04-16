import asyncio
import shutil
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path

app = FastAPI(title="Test 2 — Research Viewer")


class ResearchRequest(BaseModel):
    topics: str  # newline-separated list of topics
    prompt_extra: str = ""  # optional extra instructions


class ResearchResponse(BaseModel):
    markdown: str
    duration_seconds: float


@app.get("/api/health")
def health():
    claude_path = shutil.which("claude")
    return {
        "status": "ok",
        "experiment": "test2-research",
        "claude_cli": claude_path or "not found",
    }


@app.post("/api/research", response_model=ResearchResponse)
async def run_research(body: ResearchRequest):
    claude_path = shutil.which("claude")
    if not claude_path:
        raise HTTPException(status_code=500, detail="Claude CLI not found on this machine")

    topics = body.topics.strip()
    if not topics:
        raise HTTPException(status_code=400, detail="No topics provided")

    prompt = f"""Research the following topics and provide a comprehensive summary for each.
For each topic, include:
- A brief overview
- Key recent developments or news
- Important facts or statistics
- Relevant links if found

Topics:
{topics}

{body.prompt_extra}

Format the output as clean markdown with ## headers for each topic."""

    import time
    start = time.time()

    proc = await asyncio.create_subprocess_exec(
        claude_path,
        "-p", prompt,
        "--allowedTools", "WebSearch,WebFetch",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    duration = time.time() - start

    if proc.returncode != 0:
        err = stderr.decode().strip()
        raise HTTPException(status_code=500, detail=f"Claude CLI error: {err}")

    markdown = stdout.decode().strip()
    if not markdown:
        raise HTTPException(status_code=500, detail="Claude returned empty response")

    return ResearchResponse(markdown=markdown, duration_seconds=round(duration, 1))


# Serve UI — must be last
ui_path = Path(__file__).parent.parent / "ui"
app.mount("/", StaticFiles(directory=str(ui_path), html=True), name="ui")
