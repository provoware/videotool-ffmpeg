from __future__ import annotations

import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from paths import logs_dir


def log_exception(
    context: str,
    exc: BaseException,
    logs_path: Path | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    try:
        target_dir = logs_path or logs_dir()
        target_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "context": context,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            ).strip(),
        }
        if extra:
            payload["extra"] = extra
        log_path = target_dir / "debug.log"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        return
