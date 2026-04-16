"""
AWS Lambda handler — experiment 5.

Demonstrates:
- Lambda event/context pattern
- API Gateway HTTP API integration (v2 payload format)
- JSON responses with proper status codes
- GET/POST routing from a single handler

For local testing, run test/local_server.py which wraps this handler in a FastAPI app.
For AWS deployment, zip this file + dependencies and upload to Lambda.
"""

import json
from datetime import datetime


# In-memory store for local testing / demo
_items = [
    {"id": 1, "name": "Learn Lambda", "created_at": "2026-04-15T00:00:00"},
    {"id": 2, "name": "Set up API Gateway", "created_at": "2026-04-15T00:00:00"},
    {"id": 3, "name": "Connect to RDS", "created_at": "2026-04-15T00:00:00"},
]
_next_id = 4


def handler(event, context):
    """Main Lambda handler. Routes based on HTTP method from API Gateway v2."""
    global _items

    # API Gateway HTTP API v2 payload format
    request_context = event.get("requestContext", {})
    http_info = request_context.get("http", {})
    method = http_info.get("method", event.get("httpMethod", "GET"))
    path = http_info.get("path", event.get("path", "/"))

    try:
        if method == "GET" and path.endswith("/health"):
            return respond(200, {
                "status": "ok",
                "experiment": "test5-lambda",
                "timestamp": datetime.now().isoformat(),
                "runtime": "aws-lambda" if context else "local",
            })

        elif method == "GET" and path.endswith("/items"):
            return respond(200, {"items": _items, "count": len(_items)})

        elif method == "POST" and path.endswith("/items"):
            body = json.loads(event.get("body", "{}"))
            name = body.get("name", "").strip()
            if not name:
                return respond(400, {"error": "name is required"})
            item = create_item(name)
            return respond(201, item)

        elif method == "GET" and "/items/" in path:
            item_id = int(path.split("/items/")[1])
            item = next((i for i in _items if i["id"] == item_id), None)
            if not item:
                return respond(404, {"error": "Item not found"})
            return respond(200, item)

        elif method == "DELETE" and "/items/" in path:
            item_id = int(path.split("/items/")[1])
            before = len(_items)
            _items = [i for i in _items if i["id"] != item_id]
            if len(_items) == before:
                return respond(404, {"error": "Item not found"})
            return respond(200, {"deleted": True, "id": item_id})

        else:
            return respond(404, {"error": f"Not found: {method} {path}"})

    except Exception as e:
        return respond(500, {"error": str(e)})


def create_item(name):
    global _next_id
    item = {
        "id": _next_id,
        "name": name,
        "created_at": datetime.now().isoformat(),
    }
    _items.append(item)
    _next_id += 1
    return item


def respond(status_code, body):
    """Format response for API Gateway HTTP API v2."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }
