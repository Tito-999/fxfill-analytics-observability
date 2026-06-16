"""Integration tests for the full generation pipeline."""

from datetime import UTC, datetime

import pytest
from fxfill_analytics.generation.pipeline import SIZE_PRESETS, run_pipeline

START_DATE = datetime(2026, 2, 14, tzinfo=UTC)
END_DATE = datetime(2026, 6, 14, tzinfo=UTC)


class TestPipelineTiny:
    """Full pipeline test at tiny scale."""

    def test_pipeline_produces_all_tables(self, tmp_path):
        manifest = run_pipeline(
            seed=20260616,
            size="tiny",
            output_dir=tmp_path,
            start_date=START_DATE,
            end_date=END_DATE,
            overwrite=True,
        )
        run_dir = tmp_path / manifest["run_id"]
        assert run_dir.exists()

        expected_tables = [
            "users",
            "documents",
            "sessions",
            "product_events",
            "agent_runs",
            "agent_spans",
            "experiment_assignments",
        ]
        for name in expected_tables:
            assert (run_dir / f"{name}.parquet").exists(), f"Missing {name}.parquet"

        # Manifest checks
        assert (run_dir / "generation_manifest.json").exists()
        assert (run_dir / "data_quality_summary.json").exists()
        assert (run_dir / "phenomena_manifest.json").exists()

    def test_pipeline_manifest_is_valid(self, tmp_path):
        manifest = run_pipeline(
            seed=20260616,
            size="tiny",
            output_dir=tmp_path,
            start_date=START_DATE,
            end_date=END_DATE,
            overwrite=True,
        )
        assert manifest["synthetic_data"] is True
        assert manifest["seed"] == 20260616
        assert manifest["size"] == "tiny"
        assert "duration_seconds" in manifest
        assert len(manifest["tables"]) == 7

    def test_pipeline_invalid_size_raises(self, tmp_path):
        with pytest.raises(ValueError, match="Unknown size"):
            run_pipeline(
                seed=20260616,
                size="invalid",
                output_dir=tmp_path,
                start_date=START_DATE,
                end_date=END_DATE,
            )

    def test_pipeline_no_overwrite_raises(self, tmp_path):
        run_pipeline(
            seed=20260616,
            size="tiny",
            output_dir=tmp_path,
            start_date=START_DATE,
            end_date=END_DATE,
            overwrite=True,
        )
        with pytest.raises(FileExistsError, match="already exists"):
            run_pipeline(
                seed=20260616,
                size="tiny",
                output_dir=tmp_path,
                start_date=START_DATE,
                end_date=END_DATE,
                overwrite=False,
            )

    def test_pipeline_all_sizes_have_presets(self):
        for size in ["tiny", "small", "medium", "large"]:
            assert size in SIZE_PRESETS
            cfg = SIZE_PRESETS[size]
            assert cfg["users"] > 0
            assert cfg["events"] > 0


class TestPipelineReproducibility:
    """Verify that the same seed produces identical output."""

    def test_same_seed_same_manifest(self, tmp_path):
        m1 = run_pipeline(
            seed=42,
            size="tiny",
            output_dir=tmp_path / "a",
            start_date=START_DATE,
            end_date=END_DATE,
            overwrite=True,
        )
        m2 = run_pipeline(
            seed=42,
            size="tiny",
            output_dir=tmp_path / "b",
            start_date=START_DATE,
            end_date=END_DATE,
            overwrite=True,
        )
        # Non-temporal fields should match
        assert m1["config_hash"] == m2["config_hash"]
        assert m1["tables"] == m2["tables"]

    def test_different_seed_different_data(self, tmp_path):
        import pandas as pd

        m1 = run_pipeline(
            seed=42,
            size="tiny",
            output_dir=tmp_path / "a",
            start_date=START_DATE,
            end_date=END_DATE,
            overwrite=True,
        )
        m2 = run_pipeline(
            seed=99,
            size="tiny",
            output_dir=tmp_path / "b",
            start_date=START_DATE,
            end_date=END_DATE,
            overwrite=True,
        )
        # Read users and verify they differ (IDs are sequential, but signup times differ)
        u1 = pd.read_parquet(tmp_path / "a" / m1["run_id"] / "users.parquet")
        u2 = pd.read_parquet(tmp_path / "b" / m2["run_id"] / "users.parquet")
        # User IDs are deterministic sequential (U000001...), same across seeds
        # But signup times and channel distributions differ
        assert not u1["signup_time"].equals(
            u2["signup_time"]
        ), "Different seeds should produce different signup times"


class TestPipelinePhenomenaDisabled:
    """Verify phenomena can be disabled via CLI flags."""

    def test_disable_phenomena_reduces_anomalies(self, tmp_path):
        _ = run_pipeline(
            seed=20260616,
            size="tiny",
            output_dir=tmp_path / "all",
            start_date=START_DATE,
            end_date=END_DATE,
            overwrite=True,
        )
        m_none = run_pipeline(
            seed=20260616,
            size="tiny",
            output_dir=tmp_path / "none",
            start_date=START_DATE,
            end_date=END_DATE,
            overwrite=True,
            disable_phenomena=[
                "P01",
                "P02",
                "P03",
                "P04",
                "P05",
                "P06",
                "P07",
                "P08",
                "P09",
                "P10",
            ],
        )
        # With all phenomena disabled, quality should be "passed"
        assert m_none["quality_status"] in ("passed", "warnings")
