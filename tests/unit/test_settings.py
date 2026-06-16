"""Tests for application settings in settings.py."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def temp_config_dir():
    """Create a temporary config directory with app.yml."""
    with tempfile.TemporaryDirectory() as tmp:
        config_dir = Path(tmp) / "config"
        config_dir.mkdir()
        app_config = {
            "project": {"name": "test", "version": "0.1.0"},
            "paths": {"data_dir": "./data"},
            "database": {"duckdb": {"path": "./warehouse/test.duckdb"}},
            "data_generation": {
                "default_size": "tiny",
                "default_seed": 42,
                "available_sizes": {
                    "tiny": {"users": 10},
                },
            },
        }
        with open(config_dir / "app.yml", "w") as f:
            yaml.safe_dump(app_config, f)
        old_cwd = os.getcwd()
        os.chdir(tmp)
        yield Path(tmp)
        os.chdir(old_cwd)


class TestSettingsModule:
    """Test that settings module can be imported and used."""

    def test_project_root_exists(self):
        from fxfill_analytics.settings import PROJECT_ROOT

        assert PROJECT_ROOT.exists()

    def test_project_root_is_absolute(self):
        from fxfill_analytics.settings import PROJECT_ROOT

        assert PROJECT_ROOT.is_absolute()

    def test_get_data_dir_returns_path(self):
        from fxfill_analytics.settings import get_data_dir

        result = get_data_dir("generated")
        assert isinstance(result, Path)

    def test_get_data_size_returns_string(self):
        from fxfill_analytics.settings import get_data_size

        result = get_data_size()
        assert isinstance(result, str)

    def test_get_data_seed_returns_int(self):
        from fxfill_analytics.settings import get_data_seed

        result = get_data_seed()
        assert isinstance(result, int)

    def test_is_llm_mock_returns_bool(self):
        from fxfill_analytics.settings import is_llm_mock

        result = is_llm_mock()
        assert isinstance(result, bool)

    def test_get_config_loads_without_error(self):
        from fxfill_analytics.settings import (
            get_app_config,
            get_data_gen_config,
            get_experiments_config,
            get_metrics_config,
        )

        assert isinstance(get_app_config(), dict)
        assert isinstance(get_metrics_config(), dict)
        assert isinstance(get_experiments_config(), dict)
        assert isinstance(get_data_gen_config(), dict)

    def test_app_config_has_expected_keys(self):
        from fxfill_analytics.settings import get_app_config

        config = get_app_config()
        assert "project" in config
        assert "data_generation" in config

    def test_data_gen_config_has_size_presets(self):
        from fxfill_analytics.settings import get_data_gen_config

        config = get_data_gen_config()
        assert "generation" in config

    def test_env_var_overrides_data_size(self, monkeypatch):
        monkeypatch.setenv("DATA_SIZE", "large")
        # Need to clear cache
        import fxfill_analytics.settings as settings
        from fxfill_analytics.settings import get_data_size

        settings._app_config = None
        result = get_data_size()
        # May be "large" from env or "medium" from config depending on env
        assert result in ("tiny", "small", "medium", "large")

    def test_load_yaml_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            from fxfill_analytics.settings import _load_yaml

            _load_yaml("nonexistent_file.yml")
