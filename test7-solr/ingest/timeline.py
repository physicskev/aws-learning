"""
Timeline analysis for a raw Claude Code session .jsonl.

Given a session jsonl (one event per line, each with a `timestamp`), classify
every gap between consecutive events and split the session's total wall-clock
into three buckets:

    user_seconds      — user was thinking / typing (next event is a real user msg)
    assistant_seconds — model was thinking / generating / running tools
    idle_seconds      — gap larger than IDLE_THRESHOLD_SECONDS; presumed away-from-keyboard

A "real user message" has `type=user` and `message.content` that is either a
plain string OR a list containing at least one text block. Synthetic user
events that only carry `tool_result` blocks are counted as assistant time —
the model is the reason those events exist.

Usage:
    from timeline import compute_timeline
    t = compute_timeline(Path("path/to/session.jsonl"))
    # -> {'user_seconds': 312, 'assistant_seconds': 1205, 'idle_seconds': 0, ...}
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

IDLE_THRESHOLD_SECONDS = 600  # 10 minutes — generous enough for a user reading/thinking without walking away


def _parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        # '2026-03-30T17:17:46.861Z' -> datetime with tzinfo
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _is_real_user(event: dict) -> bool:
    """True if this event is the user genuinely saying/doing something,
    NOT a synthetic tool_result echo."""
    if event.get("type") != "user":
        return False
    msg = event.get("message")
    if not isinstance(msg, dict):
        return False
    content = msg.get("content")
    if isinstance(content, str):
        return bool(content.strip())
    if isinstance(content, list):
        # Real user content has at least one non-tool_result block with text
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_result":
                continue
            text = block.get("text") or block.get("content") or ""
            if isinstance(text, str) and text.strip():
                return True
    return False


def _is_assistantish(event: dict) -> bool:
    """Events that represent the model/tools working: assistant messages,
    system entries, tool_result user messages, and file snapshots all count."""
    t = event.get("type")
    if t == "assistant":
        return True
    if t == "user" and not _is_real_user(event):
        return True  # tool_result echo
    if t in ("system", "file-history-snapshot"):
        return True
    return False


def compute_timeline(jsonl_path: Path, idle_threshold_seconds: int = IDLE_THRESHOLD_SECONDS) -> dict:
    user_seconds = 0.0
    assistant_seconds = 0.0
    idle_seconds = 0.0
    real_user_msgs = 0
    assistant_msgs = 0
    events_with_ts = 0

    first_ts = None
    last_ts = None
    prev_ts = None

    try:
        with jsonl_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue

                ts = _parse_ts(ev.get("timestamp"))
                if ts is None:
                    continue

                events_with_ts += 1
                if first_ts is None:
                    first_ts = ts
                last_ts = ts

                if _is_real_user(ev):
                    real_user_msgs += 1
                if ev.get("type") == "assistant":
                    assistant_msgs += 1

                if prev_ts is not None:
                    dt = (ts - prev_ts).total_seconds()
                    if dt < 0:
                        dt = 0  # events occasionally land out of order; skip
                    if dt > idle_threshold_seconds:
                        idle_seconds += dt
                    elif _is_real_user(ev):
                        user_seconds += dt
                    else:
                        # Assistant messages, tool_results, system events, snapshots
                        assistant_seconds += dt
                prev_ts = ts
    except (OSError, FileNotFoundError):
        return _empty_result()

    total = user_seconds + assistant_seconds + idle_seconds
    return {
        "user_seconds": int(round(user_seconds)),
        "assistant_seconds": int(round(assistant_seconds)),
        "idle_seconds": int(round(idle_seconds)),
        "active_seconds": int(round(user_seconds + assistant_seconds)),
        "total_seconds": int(round(total)),
        "real_user_msgs": real_user_msgs,
        "assistant_msgs": assistant_msgs,
        "event_count": events_with_ts,
        "first_ts": first_ts.strftime("%Y-%m-%dT%H:%M:%SZ") if first_ts else None,
        "last_ts": last_ts.strftime("%Y-%m-%dT%H:%M:%SZ") if last_ts else None,
    }


def _empty_result() -> dict:
    return {
        "user_seconds": None, "assistant_seconds": None, "idle_seconds": None,
        "active_seconds": None, "total_seconds": None,
        "real_user_msgs": 0, "assistant_msgs": 0, "event_count": 0,
        "first_ts": None, "last_ts": None,
    }


if __name__ == "__main__":
    import sys
    from pprint import pprint
    path = Path(sys.argv[1])
    pprint(compute_timeline(path))
