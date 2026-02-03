from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class PathCheckResult:
    path: Path
    label: str


class PathValidationError(ValueError):
    pass


def _ensure_no_null_bytes(path: Path, label: str) -> Path:
    raw = str(path)
    if "\x00" in raw:
        raise PathValidationError(f"{label} enthält ein ungültiges Zeichen.")
    return path


def ensure_existing_file(path: Path, label: str) -> Path:
    path = _ensure_no_null_bytes(Path(path).expanduser(), label)
    resolved = path.resolve(strict=False)
    if not resolved.exists():
        raise PathValidationError(f"{label} nicht gefunden: {resolved}")
    if not resolved.is_file():
        raise PathValidationError(f"{label} ist keine Datei: {resolved}")
    return resolved


def ensure_existing_dir(path: Path, label: str, create: bool = False) -> Path:
    path = _ensure_no_null_bytes(Path(path).expanduser(), label)
    resolved = path.resolve(strict=False)
    if not resolved.exists():
        if create:
            resolved.mkdir(parents=True, exist_ok=True)
        else:
            raise PathValidationError(f"{label} nicht gefunden: {resolved}")
    if not resolved.is_dir():
        raise PathValidationError(f"{label} ist kein Ordner: {resolved}")
    return resolved


def ensure_output_path(path: Path, label: str) -> Path:
    path = _ensure_no_null_bytes(Path(path).expanduser(), label)
    resolved = path.resolve(strict=False)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    if not resolved.parent.is_dir():
        raise PathValidationError(f"{label} hat keinen gültigen Zielordner: {resolved}")
    if resolved.exists() and resolved.is_dir():
        raise PathValidationError(f"{label} verweist auf einen Ordner: {resolved}")
    test_path = resolved.parent / f".write_test_{uuid4().hex}.tmp"
    try:
        test_path.write_text("ok", encoding="utf-8")
    except Exception as exc:
        raise PathValidationError(
            f"{label} ist im Zielordner nicht schreibbar: {resolved.parent}"
        ) from exc
    finally:
        test_path.unlink(missing_ok=True)
    return resolved
