#!/usr/bin/env python3
"""
Zentrale Pfade (Paths) für die Portable-Struktur.
Ziel: Weniger Duplikate, klare Trennung von System- und Variablen-Daten.
"""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def app_dir() -> Path:
    return repo_root() / "app"


def assets_dir() -> Path:
    return repo_root() / "assets"


def portable_data_dir() -> Path:
    return repo_root() / "portable_data"


def config_dir() -> Path:
    return portable_data_dir() / "config"


def data_dir() -> Path:
    return portable_data_dir() / "user_data"


def cache_dir() -> Path:
    return portable_data_dir() / "cache"


def logs_dir() -> Path:
    return portable_data_dir() / "logs"


def venv_dir() -> Path:
    return portable_data_dir() / ".venv"
