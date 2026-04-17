from __future__ import annotations

from pathlib import Path
from typing import Any

from src.utils.paths import PROJECT_ROOT


def load_yaml_config(relative_path: str, default: dict[str, Any] | None = None) -> dict[str, Any]:
    config_path = PROJECT_ROOT / relative_path
    if not config_path.exists():
        return dict(default or {})

    try:
        import yaml  # type: ignore
    except ImportError:
        return dict(default or {})

    loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        return dict(default or {})
    return loaded
