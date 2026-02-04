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
            try:
                resolved.mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                raise PathValidationError(
                    f"{label} konnte nicht erstellt werden: {resolved}"
                ) from exc
        else:
            raise PathValidationError(f"{label} nicht gefunden: {resolved}")
    if not resolved.is_dir():
        raise PathValidationError(f"{label} ist kein Ordner: {resolved}")
    return resolved


def ensure_output_path(path: Path, label: str) -> Path:
    path = _ensure_no_null_bytes(Path(path).expanduser(), label)
    resolved = path.resolve(strict=False)
    if resolved.parent.exists() and not resolved.parent.is_dir():
        raise PathValidationError(
            f"{label} hat keinen gültigen Zielordner: {resolved.parent}"
        )
    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise PathValidationError(
            f"{label} hat keinen gültigen Zielordner: {resolved.parent}"
        ) from exc
    if not resolved.parent.is_dir():
        raise PathValidationError(
            f"{label} hat keinen gültigen Zielordner: {resolved.parent}"
        )
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


def validate_settings_schema(settings: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(settings, dict):
        return ["settings_root:not_a_dict"]

    def expect_dict(value: object, key: str) -> dict:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        errors.append(f"{key}:not_a_dict")
        return {}

    def expect_type(value: object, key: str, expected: type) -> None:
        if value is None:
            return
        if not isinstance(value, expected):
            errors.append(f"{key}:not_{expected.__name__}")

    paths = expect_dict(settings.get("paths"), "paths")
    maintenance = expect_dict(settings.get("maintenance"), "maintenance")
    performance = expect_dict(settings.get("performance"), "performance")
    ui = expect_dict(settings.get("ui"), "ui")

    expect_type(paths.get("watch_folder"), "paths.watch_folder", str)
    expect_type(paths.get("base_data_dir"), "paths.base_data_dir", str)
    for key in (
        "exports_dir",
        "reports_dir",
        "staging_dir",
        "trash_dir",
        "library_audio_dir",
        "library_images_dir",
        "quarantine_dir",
        "quarantine_jobs_dir",
    ):
        expect_type(paths.get(key), f"paths.{key}", str)

    expect_type(maintenance.get("min_free_mb"), "maintenance.min_free_mb", int)

    expect_type(performance.get("eco_mode"), "performance.eco_mode", bool)
    expect_type(performance.get("eco_threads"), "performance.eco_threads", int)
    expect_type(performance.get("normal_threads"), "performance.normal_threads", int)

    expect_type(ui.get("zoom_percent"), "ui.zoom_percent", int)
    expect_type(ui.get("language"), "ui.language", str)
    return errors


def validate_settings_paths(settings: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(settings, dict):
        return ["settings_root:not_a_dict"]
    paths = settings.get("paths")
    if paths is None:
        return errors
    if not isinstance(paths, dict):
        return ["paths:not_a_dict"]

    def check_string(value: object, key: str, allow_empty: bool = False) -> None:
        if value is None:
            return
        if not isinstance(value, str):
            errors.append(f"{key}:not_a_string")
            return
        if not value.strip() and not allow_empty:
            errors.append(f"{key}:empty")
            return
        if "\x00" in value:
            errors.append(f"{key}:null_byte")

    def check_relative(value: object, key: str) -> None:
        check_string(value, key)
        if not isinstance(value, str) or not value.strip():
            return
        candidate = Path(value)
        if candidate.is_absolute():
            errors.append(f"{key}:absolute_path")
            return
        if ".." in candidate.parts:
            errors.append(f"{key}:parent_traversal")

    def check_base_dir(value: object, key: str) -> None:
        check_string(value, key)
        if not isinstance(value, str) or not value.strip():
            return
        candidate = Path(value).expanduser()
        if ".." in candidate.parts:
            errors.append(f"{key}:parent_traversal")

    check_string(paths.get("watch_folder"), "paths.watch_folder", allow_empty=True)
    check_base_dir(paths.get("base_data_dir"), "paths.base_data_dir")
    for key in (
        "exports_dir",
        "reports_dir",
        "staging_dir",
        "trash_dir",
        "library_audio_dir",
        "library_images_dir",
        "quarantine_dir",
        "quarantine_jobs_dir",
    ):
        check_relative(paths.get(key), f"paths.{key}")
    return errors
