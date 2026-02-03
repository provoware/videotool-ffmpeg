from __future__ import annotations

import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from paths import logs_dir


def _write_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def log_message(
    message: str,
    *,
    level: str = "INFO",
    context: str | None = None,
    logs_path: Path | None = None,
    user_message: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    try:
        target_dir = logs_path or logs_dir()
        payload = {
            "at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "level": level,
            "message": message,
        }
        if context:
            payload["context"] = context
        if extra:
            payload["extra"] = extra
        _write_jsonl(target_dir / "debug.log", payload)
        if user_message:
            user_payload = {
                "at": payload["at"],
                "level": "USER",
                "message": user_message,
            }
            if context:
                user_payload["context"] = context
            _write_jsonl(target_dir / "user_feedback.log", user_payload)
    except Exception:
        return


def log_exception(
    context: str,
    exc: BaseException,
    logs_path: Path | None = None,
    extra: dict[str, Any] | None = None,
    user_message: str | None = None,
) -> None:
    error_payload = {
        "error_type": type(exc).__name__,
        "error": str(exc),
        "traceback": "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        ).strip(),
    }
    if extra:
        error_payload["extra"] = extra
    log_message(
        f"Exception in {context}",
        level="ERROR",
        context=context,
        logs_path=logs_path,
        user_message=user_message,
        extra=error_payload,
    )
