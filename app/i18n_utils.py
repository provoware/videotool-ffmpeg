from __future__ import annotations

from pathlib import Path

from io_utils import load_json
from paths import config_dir


def _language_key(raw: object, fallback: str) -> str:
    if not isinstance(raw, str):
        return fallback
    key = raw.strip().lower()
    return key or fallback


def _texts_path(language: str) -> Path:
    return config_dir() / f"texte_{language}.json"


def _merge_texts(base: dict, override: dict) -> dict:
    merged = {"strings": {}, "tooltips": {}}
    for section in ("strings", "tooltips"):
        base_section = base.get(section, {}) if isinstance(base, dict) else {}
        override_section = (
            override.get(section, {}) if isinstance(override, dict) else {}
        )
        if not isinstance(base_section, dict):
            base_section = {}
        if not isinstance(override_section, dict):
            override_section = {}
        merged[section] = {**base_section, **override_section}
    return merged


def load_texts(settings: dict, *, fallback_language: str = "de") -> dict:
    fallback = _language_key(fallback_language, "de")
    language = _language_key(settings.get("ui", {}).get("language"), fallback)
    primary_path = _texts_path(language)
    primary = load_json(
        primary_path,
        {"strings": {}, "tooltips": {}},
        context="load_texts_primary",
    )
    if language == fallback:
        return primary
    fallback_path = _texts_path(fallback)
    fallback_texts = load_json(
        fallback_path,
        {"strings": {}, "tooltips": {}},
        context="load_texts_fallback",
    )
    return _merge_texts(fallback_texts, primary)
