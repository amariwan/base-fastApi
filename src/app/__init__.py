"""Kompatibilitäts-Shim: Ermöglicht Build-Tools, das vorhandene `app/` zu finden.

Dieser kleine Shim fügt den Pfad zur existierenden Top-Level-`app`-Quelle
zur `__path__`-Suche hinzu, falls ein Builder ein `src/`-Layout erwartet.
"""
from __future__ import annotations

import os
from pathlib import Path

_here = Path(__file__).resolve().parent
_real_app = (_here.parent.parent / "app").resolve()

if _real_app.exists():
    __path__.insert(0, str(_real_app))
