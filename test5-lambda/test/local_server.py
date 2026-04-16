"""
Local test server that wraps the Lambda handler in a FastAPI app.
Simulates API Gateway HTTP API v2 event format.

Usage:
    cd test5-lambda/test
    uv run uvicorn local_server:app --port 8005 --reload
"""

import sys
import json
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Add function dir to path so we can import the handler
sys.path.insert(0, str(Path(__file__).parent.parent / "function"))
from lambda_handler import handler

app = FastAPI(title="Test 5 — Lambda (Local)")


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_to_lambda(request: Request, path: str):
    """Convert HTTP request to Lambda event format and call the handler."""

    body = None
    if request.method in ("POST", "PUT", "PATCH"):
        body = await request.body()
        body = body.decode("utf-8") if body else None

    # Build API Gateway v2 event
    event = {
        "requestContext": {
            "http": {
                "method": request.method,
                "path": f"/api/{path}",
            }
        },
        "headers": dict(request.headers),
        "queryStringParameters": dict(request.query_params) or None,
        "body": body,
    }

    # Call the Lambda handler (context=None for local)
    result = handler(event, None)

    return JSONResponse(
        status_code=result["statusCode"],
        content=json.loads(result["body"]),
        headers={k: v for k, v in result.get("headers", {}).items() if k != "Content-Type"},
    )


@app.get("/api/health")
async def health_direct():
    """Direct health check (bypasses Lambda for quick verification)."""
    return {"status": "ok", "mode": "local-fastapi-wrapper"}
