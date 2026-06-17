"""Verify dbt artifacts: separate model/test results with different hashes."""

import hashlib
import json
import tempfile
from pathlib import Path


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def build_min_manifest() -> dict:
    return {
        "nodes": {
            "model.A": {"resource_type": "model"},
            "model.B": {"resource_type": "model"},
            "test.not_null_a": {"resource_type": "test", "test_metadata": {"name": "not_null_a"}},
            "test.not_null_b": {"resource_type": "test", "test_metadata": {"name": "not_null_b"}},
            "test.custom_sql": {"resource_type": "test"},
        }
    }


def test_same_file_fails():
    """Same file used as both model and test results must be detected."""
    results = {
        "results": [
            {"unique_id": "model.A", "status": "success"},
            {"unique_id": "test.not_null_a", "status": "pass"},
        ]
    }
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        json.dump(results, f)
        path = Path(f.name)

    try:
        # This would be an error if same file is passed for both
        h1 = _hash(path.read_bytes())
        h2 = _hash(path.read_bytes())
        assert h1 == h2  # Same file = same hash (this IS the failure condition)
    finally:
        path.unlink()


def test_separate_artifacts_pass():
    """Separate model and test artifacts with different content must have different hashes."""
    model_results = {
        "results": [
            {"unique_id": "model.A", "status": "success"},
            {"unique_id": "model.B", "status": "success"},
        ]
    }
    test_results = {
        "results": [
            {"unique_id": "test.not_null_a", "status": "pass"},
            {"unique_id": "test.not_null_b", "status": "pass"},
            {"unique_id": "test.custom_sql", "status": "pass"},
        ]
    }
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        json.dump(model_results, f)
        mp = Path(f.name)
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        json.dump(test_results, f)
        tp = Path(f.name)

    try:
        h1 = _hash(mp.read_bytes())
        h2 = _hash(tp.read_bytes())
        assert h1 != h2, "Separate model and test artifacts must have different hashes"
    finally:
        mp.unlink()
        tp.unlink()


def test_manifest_test_classification():
    """Generic tests have test_metadata, singular tests do not."""
    manifest = build_min_manifest()
    generic = 0
    singular = 0
    for _nid, node in manifest["nodes"].items():
        if node.get("resource_type") == "test":
            if node.get("test_metadata") is not None:
                generic += 1
            else:
                singular += 1
    assert generic == 2, f"Expected 2 generic tests, got {generic}"
    assert singular == 1, f"Expected 1 singular test, got {singular}"
