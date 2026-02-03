from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from logging_utils import log_exception


class JsonWriteError(RuntimeError):
    pass


class FileLockTimeoutError(RuntimeError):
    pass


def _validate_json_path(path: Path) -> tuple[bool, str]:
    if not isinstance(path, Path):
        return False, "not_a_path"
    raw = str(path)
    if "\x00" in raw:
        return False, "null_byte"
    if not path.name:
        return False, "empty_name"
    if path.suffix.lower() != ".json":
        return False, "wrong_suffix"
    return True, ""


def _default_payload(default: Any | None) -> Any:
    return default if default is not None else {}


def load_json(
    path: Path,
    default: Any | None = None,
    *,
    expect_type: type | tuple[type, ...] | None = dict,
    context: str = "load_json",
) -> Any:
    valid, reason = _validate_json_path(path)
    if not valid:
        log_exception(
            context,
            ValueError("Ungültiger JSON-Pfad"),
            extra={"path": str(path), "reason": reason},
        )
        return _default_payload(default)
    if not path.exists():
        return _default_payload(default)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log_exception(context, exc, extra={"path": str(path)})
        return _default_payload(default)
    if expect_type and not isinstance(data, expect_type):
        log_exception(
            context,
            ValueError("Unerwarteter JSON-Typ"),
            extra={"path": str(path), "expected": str(expect_type)},
        )
        return _default_payload(default)
    return data


def _acquire_lock(
    lock_path: Path,
    *,
    timeout_s: float,
    stale_s: float,
) -> int:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.write(fd, f"pid={os.getpid()}".encode("utf-8"))
            return fd
        except FileExistsError:
            try:
                age = time.time() - lock_path.stat().st_mtime
            except FileNotFoundError:
                age = 0
            if age > stale_s:
                lock_path.unlink(missing_ok=True)
                continue
            if time.monotonic() - start > timeout_s:
                raise FileLockTimeoutError(f"Lock-Zeitüberschreitung: {lock_path}")
            time.sleep(0.1)


def _release_lock(lock_path: Path, fd: int) -> None:
    try:
        os.close(fd)
    finally:
        lock_path.unlink(missing_ok=True)


def atomic_write_json(
    path: Path,
    payload: Any,
    *,
    context: str = "atomic_write_json",
    indent: int = 2,
    lock_timeout_s: float = 6.0,
    stale_lock_s: float = 60.0,
    verify: bool = True,
) -> bool:
    valid, reason = _validate_json_path(path)
    if not valid:
        log_exception(
            context,
            ValueError("Ungültiger JSON-Pfad"),
            extra={"path": str(path), "reason": reason},
        )
        return False
    try:
        encoded = json.dumps(payload, ensure_ascii=False, indent=indent)
    except (TypeError, ValueError) as exc:
        log_exception(context, exc, extra={"path": str(path)})
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_fd = None
    tmp_path = None
    try:
        lock_fd = _acquire_lock(
            lock_path, timeout_s=lock_timeout_s, stale_s=stale_lock_s
        )
        fd, tmp_name = tempfile.mkstemp(
            dir=str(path.parent), prefix=f".{path.stem}.", suffix=".tmp"
        )
        tmp_path = Path(tmp_name)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        if verify:
            sentinel = object()
            loaded = load_json(path, default=sentinel, context=context)
            if loaded is sentinel:
                raise JsonWriteError(
                    "JSON-Validierung nach dem Schreiben fehlgeschlagen"
                )
        return True
    except Exception as exc:
        log_exception(context, exc, extra={"path": str(path)})
        return False
    finally:
        if lock_fd is not None:
            _release_lock(lock_path, lock_fd)
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
