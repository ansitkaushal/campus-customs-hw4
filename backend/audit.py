"""Append-only audit trail of agent-loop activity: output/audit_trail.json.

Every chat turn adds entries for each model step, each tool call (short args +
short result), each retry, and one "run_end" entry with the stop reason.

The file is always a valid JSON array, and it is only ever appended to: new
entries are written over the closing "]" at the end of the file, so earlier
entries are never rewritten and nothing is wiped between server runs.

Privacy: emails and long digit runs (card/phone numbers) are redacted, the
customer is logged as "user:<id>" or "guest", and text is truncated.
"""

from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)

from db import PROJECT_ROOT

AUDIT_PATH = PROJECT_ROOT / "output" / "audit_trail.json"
MAX_TEXT = 160  # characters kept from args / results / messages
OUTPUT_TOOL = "final_result"

_lock = threading.Lock()
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_LONG_NUMBER = re.compile(r"\b\d(?:[ -]?\d){9,18}\b")  # 10-19 digits: phone / card numbers


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _iso(ts: datetime | None) -> str:
    return ts.astimezone(timezone.utc).isoformat(timespec="milliseconds") if ts else _now()


def short(value: Any, limit: int = MAX_TEXT) -> str:
    """Compact, redacted, truncated text for the log."""
    text = value if isinstance(value, str) else json.dumps(value, default=str, ensure_ascii=False)
    text = _LONG_NUMBER.sub("[number]", _EMAIL.sub("[email]", " ".join(text.split())))
    return text if len(text) <= limit else text[: limit - 1] + "…"


def append(entries: list[dict]) -> None:
    """Append entries to the JSON array file without rewriting what's already there."""
    if not entries:
        return
    body = ",\n".join(json.dumps(e, ensure_ascii=False) for e in entries)
    with _lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not AUDIT_PATH.exists() or AUDIT_PATH.stat().st_size == 0:
            AUDIT_PATH.write_text(f"[\n{body}\n]\n", encoding="utf-8")
            return
        with open(AUDIT_PATH, "rb+") as f:
            # Find the closing "]" (skipping trailing whitespace) and write over it.
            f.seek(0, os.SEEK_END)
            pos = f.tell()
            while pos > 0:
                pos -= 1
                f.seek(pos)
                ch = f.read(1)
                if not ch.isspace():
                    break
            if ch != b"]":
                raise ValueError(f"{AUDIT_PATH} is not a JSON array; refusing to modify it")
            f.seek(pos)
            prev = pos - 1
            # Is the array empty ("[]")? Then no leading comma.
            while prev >= 0:
                f.seek(prev)
                c = f.read(1)
                if not c.isspace():
                    break
                prev -= 1
            sep = "\n" if c == b"[" else ",\n"
            f.seek(pos)
            f.truncate()
            f.write(f"{sep}{body}\n]\n".encode("utf-8"))


def _tool_result_summary(part: ToolReturnPart) -> str:
    if part.tool_name == "get_customer_profile":
        # Never copy account details into the log, only the shape of the answer.
        content = part.content
        logged_in = getattr(content, "logged_in", None)
        viewed = len(getattr(content, "recently_viewed_in_chat", []) or [])
        return f"profile (logged_in={logged_in}, recently_viewed={viewed})"
    return short(part.model_response_str())


def run_entries(
    run_id: str,
    messages: list[ModelMessage],
    *,
    who: str,
    page: str,
    message: str,
    mode: str,
    stop_reason: str,
    started_at: datetime | None = None,
    usage: Any = None,
    duration_s: float | None = None,
    extra: dict | None = None,
) -> list[dict]:
    """Build audit entries for one agent run from its new messages."""
    entries: list[dict] = [
        {
            "time": _iso(started_at),
            "run_id": run_id,
            "event": "run_start",
            "mode": mode,
            "who": who,
            "page": page,
            "message": short(message),
        }
    ]
    calls: dict[str, ToolCallPart] = {}
    step = 0
    for m in messages:
        if isinstance(m, ModelResponse):
            step += 1
            tool_names = [p.tool_name for p in m.parts if isinstance(p, ToolCallPart)]
            entries.append(
                {
                    "time": _iso(m.timestamp),
                    "run_id": run_id,
                    "event": "model_step",
                    "step": step,
                    "finish_reason": m.finish_reason,
                    "requested_tools": tool_names,
                    "text": short(" ".join(p.content for p in m.parts if isinstance(p, TextPart))) or None,
                }
            )
            for p in m.parts:
                if isinstance(p, ToolCallPart):
                    calls[p.tool_call_id] = p
        elif isinstance(m, ModelRequest):
            for p in m.parts:
                if isinstance(p, ToolReturnPart):
                    call = calls.get(p.tool_call_id)
                    if p.tool_name == OUTPUT_TOOL:
                        continue  # the final answer is summarized in run_end
                    entries.append(
                        {
                            "time": _iso(p.timestamp),
                            "run_id": run_id,
                            "event": "tool_call",
                            "tool": p.tool_name,
                            "args": short(call.args_as_json_str() if call else ""),
                            "result": _tool_result_summary(p),
                            "ok": True,
                        }
                    )
                elif isinstance(p, RetryPromptPart):
                    call = calls.get(p.tool_call_id) if p.tool_call_id else None
                    is_output = p.tool_name == OUTPUT_TOOL
                    entries.append(
                        {
                            "time": _iso(p.timestamp),
                            "run_id": run_id,
                            "event": "output_retry" if is_output else "tool_call",
                            "tool": p.tool_name,
                            "args": None if is_output else short(call.args_as_json_str() if call else ""),
                            "result": short(p.model_response()),
                            "ok": False,
                        }
                    )

    end: dict[str, Any] = {
        "time": _now(),
        "run_id": run_id,
        "event": "run_end",
        "stop_reason": stop_reason,
        "model_steps": step,
    }
    if usage is not None:
        end.update(
            requests=usage.requests,
            tool_calls=usage.tool_calls,
            input_tokens=usage.input_tokens,
            cached_tokens=usage.cache_read_tokens,
            output_tokens=usage.output_tokens,
        )
    if duration_s is not None:
        end["duration_s"] = round(duration_s, 2)
    if extra:
        end.update(extra)
    entries.append(end)
    return entries


def log_event(event: str, **fields: Any) -> None:
    """One-off entry (e.g. a rate-limited request that never reached the agent)."""
    append([{"time": _now(), "event": event, **{k: short(v) if isinstance(v, str) else v for k, v in fields.items()}}])
