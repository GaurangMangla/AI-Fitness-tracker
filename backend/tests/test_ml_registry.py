"""Tests for `app.ml.registry` — model/preprocessor loading, caching, and
error handling.

Uses `reset_for_testing()` before/after each test so the module-level cache
doesn't leak between tests — without it, whichever test runs first would
determine every subsequent test's result regardless of what that later test
actually configures.
"""

import joblib
import pytest

from app.core.config import get_settings
from app.ml import registry
from app.ml.registry import ModelLoadError, get_model_and_preprocessor
from tests.ml_test_helpers import build_tiny_model_and_preprocessor


@pytest.fixture(autouse=True)
def _reset_registry():
    registry.reset_for_testing()
    yield
    registry.reset_for_testing()


@pytest.fixture
def real_model_files(tmp_path, monkeypatch):
    """Writes a real, tiny model+preprocessor to disk and points
    ML_MODEL_PATH/ML_PREPROCESSOR_PATH at them via environment variables."""
    model, preprocessor = build_tiny_model_and_preprocessor()

    model_path = tmp_path / "model.joblib"
    preprocessor_path = tmp_path / "preprocessor.joblib"
    joblib.dump(model, model_path)
    joblib.dump(preprocessor, preprocessor_path)

    monkeypatch.setenv("ML_MODEL_PATH", str(model_path))
    monkeypatch.setenv("ML_PREPROCESSOR_PATH", str(preprocessor_path))
    get_settings.cache_clear()
    yield model_path, preprocessor_path
    get_settings.cache_clear()


class TestModelLoading:
    def test_loads_successfully_when_files_exist(self, real_model_files):
        model, preprocessor = get_model_and_preprocessor()
        assert model is not None
        assert preprocessor is not None
        assert hasattr(model, "predict_proba")
        assert hasattr(preprocessor, "transform")

    def test_second_call_returns_the_same_cached_objects(self, real_model_files):
        model_1, preprocessor_1 = get_model_and_preprocessor()
        model_2, preprocessor_2 = get_model_and_preprocessor()
        assert model_1 is model_2
        assert preprocessor_1 is preprocessor_2

    def test_raises_model_load_error_when_model_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ML_MODEL_PATH", str(tmp_path / "does_not_exist.joblib"))
        monkeypatch.setenv("ML_PREPROCESSOR_PATH", str(tmp_path / "also_missing.joblib"))
        get_settings.cache_clear()

        with pytest.raises(ModelLoadError):
            get_model_and_preprocessor()

        get_settings.cache_clear()

    def test_raises_model_load_error_when_preprocessor_file_missing(self, tmp_path, monkeypatch):
        model, _ = build_tiny_model_and_preprocessor()
        model_path = tmp_path / "model.joblib"
        joblib.dump(model, model_path)

        monkeypatch.setenv("ML_MODEL_PATH", str(model_path))
        monkeypatch.setenv("ML_PREPROCESSOR_PATH", str(tmp_path / "missing_preprocessor.joblib"))
        get_settings.cache_clear()

        with pytest.raises(ModelLoadError):
            get_model_and_preprocessor()

        get_settings.cache_clear()

    def test_load_failure_is_cached_not_retried_every_call(self, tmp_path, monkeypatch):
        """A missing/corrupt model shouldn't mean every single recommendation
        request re-hits the filesystem and re-attempts a doomed load."""
        monkeypatch.setenv("ML_MODEL_PATH", str(tmp_path / "nope.joblib"))
        monkeypatch.setenv("ML_PREPROCESSOR_PATH", str(tmp_path / "nope2.joblib"))
        get_settings.cache_clear()

        with pytest.raises(ModelLoadError):
            get_model_and_preprocessor()

        # Second call should raise the same cached error, not attempt to
        # reload — verified indirectly via the _load_attempted flag.
        assert registry._load_attempted is True
        with pytest.raises(ModelLoadError):
            get_model_and_preprocessor()

        get_settings.cache_clear()

    def test_raises_model_load_error_on_corrupted_file(self, tmp_path, monkeypatch):
        corrupt_path = tmp_path / "corrupt.joblib"
        corrupt_path.write_text("this is not a valid joblib file")

        _, preprocessor = build_tiny_model_and_preprocessor()
        preprocessor_path = tmp_path / "preprocessor.joblib"
        joblib.dump(preprocessor, preprocessor_path)

        monkeypatch.setenv("ML_MODEL_PATH", str(corrupt_path))
        monkeypatch.setenv("ML_PREPROCESSOR_PATH", str(preprocessor_path))
        get_settings.cache_clear()

        with pytest.raises(ModelLoadError):
            get_model_and_preprocessor()

        get_settings.cache_clear()

    def test_gives_a_clear_actionable_error_for_an_unpulled_git_lfs_pointer_file(
        self, tmp_path, monkeypatch
    ):
        """A real bug found while building this integration: `ml/models/*.joblib`
        is a Git LFS pointer file (a small plain-text stub, not the actual
        model) whenever LFS isn't installed or `git lfs pull` hasn't run —
        this happens on a completely ordinary `git clone`. Loading it with
        `joblib.load()` previously failed with an opaque `KeyError` deep
        inside pickle parsing (logged as just the string "118", no
        indication of the real, common, fixable cause). This test locks in
        the fix: pointer files are detected up front and produce a clear
        message pointing at the real problem.
        """
        pointer_path = tmp_path / "model.joblib"
        pointer_path.write_text(
            "version https://git-lfs.github.com/spec/v1\n"
            "oid sha256:395a0999edea1baca171390ad38078bdfb8181614fc78cb26a03377429c2c4f1\n"
            "size 74496721\n"
        )
        _, preprocessor = build_tiny_model_and_preprocessor()
        preprocessor_path = tmp_path / "preprocessor.joblib"
        joblib.dump(preprocessor, preprocessor_path)

        monkeypatch.setenv("ML_MODEL_PATH", str(pointer_path))
        monkeypatch.setenv("ML_PREPROCESSOR_PATH", str(preprocessor_path))
        get_settings.cache_clear()

        with pytest.raises(ModelLoadError, match="Git LFS pointer file"):
            get_model_and_preprocessor()

        get_settings.cache_clear()


class TestModelVersion:
    def test_get_model_version_returns_none_before_any_load_attempt(self):
        assert registry.get_model_version() is None

    def test_get_model_version_returns_the_version_from_metadata_json(self, tmp_path, monkeypatch):
        import json

        model, preprocessor = build_tiny_model_and_preprocessor()
        model_path = tmp_path / "model.joblib"
        preprocessor_path = tmp_path / "preprocessor.joblib"
        joblib.dump(model, model_path)
        joblib.dump(preprocessor, preprocessor_path)

        # metadata.json must sit next to model.joblib, matching production layout.
        with open(tmp_path / "metadata.json", "w") as f:
            json.dump({"model_version": "test-v99"}, f)

        monkeypatch.setenv("ML_MODEL_PATH", str(model_path))
        monkeypatch.setenv("ML_PREPROCESSOR_PATH", str(preprocessor_path))
        get_settings.cache_clear()

        get_model_and_preprocessor()  # triggers the load
        assert registry.get_model_version() == "test-v99"

        get_settings.cache_clear()

    def test_get_model_version_is_none_when_metadata_json_missing(self, real_model_files):
        # real_model_files fixture doesn't write a metadata.json alongside
        # the model — confirms this is handled gracefully, not an error.
        get_model_and_preprocessor()
        assert registry.get_model_version() is None


class TestGetStatus:
    def test_status_before_any_load_attempt(self):
        status = registry.get_status()
        assert status["attempted"] is False
        assert status["loaded"] is False
        assert status["model_version"] is None
        assert status["error"] is None

    def test_status_after_successful_load(self, real_model_files):
        get_model_and_preprocessor()
        status = registry.get_status()
        assert status["attempted"] is True
        assert status["loaded"] is True
        assert status["error"] is None

    def test_status_after_failed_load(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ML_MODEL_PATH", str(tmp_path / "nope.joblib"))
        monkeypatch.setenv("ML_PREPROCESSOR_PATH", str(tmp_path / "nope2.joblib"))
        get_settings.cache_clear()

        try:
            get_model_and_preprocessor()
        except ModelLoadError:
            pass

        status = registry.get_status()
        assert status["attempted"] is True
        assert status["loaded"] is False
        assert status["error"] is not None

        get_settings.cache_clear()

    def test_status_never_triggers_a_load_itself(self, real_model_files):
        """Calling get_status() before ever calling get_model_and_preprocessor()
        must not itself cause a load — this is what makes hitting the health
        check safe to do without side effects."""
        status = registry.get_status()
        assert status["attempted"] is False  # confirms get_status() didn't trigger anything
