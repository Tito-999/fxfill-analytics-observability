"""
Application settings loaded from YAML configuration and environment variables.

All paths are resolved relative to the project root.
"""

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv

# Load .env if present (do not fail if missing)
load_dotenv()

# ── Project Root ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_yaml(filename: str) -> dict[str, Any]:
    """Load a YAML config file from the config directory."""
    config_path = PROJECT_ROOT / "config" / filename
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get_env(key: str, default: Any = None) -> Any:
    """Get an environment variable with fallback to default."""
    return os.environ.get(key, default)


# ── App Config (lazy-loaded) ──
_app_config: Optional[dict[str, Any]] = None
_metrics_config: Optional[dict[str, Any]] = None
_experiments_config: Optional[dict[str, Any]] = None
_data_gen_config: Optional[dict[str, Any]] = None


def get_app_config() -> dict[str, Any]:
    global _app_config
    if _app_config is None:
        _app_config = _load_yaml("app.yml")
    return _app_config


def get_metrics_config() -> dict[str, Any]:
    global _metrics_config
    if _metrics_config is None:
        _metrics_config = _load_yaml("metrics.yml")
    return _metrics_config


def get_experiments_config() -> dict[str, Any]:
    global _experiments_config
    if _experiments_config is None:
        _experiments_config = _load_yaml("experiments.yml")
    return _experiments_config


def get_data_gen_config() -> dict[str, Any]:
    global _data_gen_config
    if _data_gen_config is None:
        _data_gen_config = _load_yaml("data_generation.yml")
    return _data_gen_config


# ── Convenience Accessors ──
def get_duckdb_path() -> Path:
    """Return the resolved DuckDB database path."""
    configured = _get_env("DUCKDB_PATH") or get_app_config()["database"]["duckdb"]["path"]
    path = Path(configured)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def get_data_dir(subdir: str = "generated") -> Path:
    """Return a resolved data subdirectory path."""
    configured = _get_env("DATA_DIR") or get_app_config()["paths"]["data_dir"]
    base = Path(configured)
    if not base.is_absolute():
        base = PROJECT_ROOT / base
    return base / subdir


def get_data_size() -> str:
    """Return the configured data generation size."""
    return _get_env("DATA_SIZE") or get_app_config()["data_generation"]["default_size"]


def get_data_seed() -> int:
    """Return the configured data generation random seed."""
    return int(_get_env("DATA_SEED") or get_app_config()["data_generation"]["default_seed"])


def is_llm_mock() -> bool:
    """Check if LLM provider is set to mock (no real LLM calls)."""
    return _get_env("LLM_PROVIDER", "mock") == "mock"
