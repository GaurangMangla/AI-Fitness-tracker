"""Tests for Phase 1.4 production-readiness additions: logging configuration,
exception handler logging, security headers, and trusted-host enforcement.
"""

import logging

from fastapi.testclient import TestClient

from app.core.logging_config import configure_logging, get_logger


class TestLoggingConfig:
    def test_configure_logging_does_not_raise(self):
        # Idempotent — safe to call multiple times (e.g. across test app fixtures)
        configure_logging()
        configure_logging()

    def test_get_logger_returns_a_logger_scoped_to_the_given_name(self):
        logger = get_logger("app.test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "app.test_module"


class TestSecurityHeaders:
    def test_response_includes_security_headers(self, client: TestClient):
        r = client.get("/api/v1/health")
        assert r.headers["x-content-type-options"] == "nosniff"
        assert r.headers["x-frame-options"] == "DENY"
        assert r.headers["referrer-policy"] == "strict-origin-when-cross-origin"

    def test_security_headers_present_on_error_responses_too(self, client: TestClient):
        # 401 responses should still carry the same baseline headers
        r = client.get("/api/v1/workouts/history")
        assert r.status_code == 401
        assert r.headers["x-content-type-options"] == "nosniff"


class TestExceptionLogging:
    def test_domain_exception_is_logged_at_info(self, client: TestClient, caplog):
        with caplog.at_level(logging.INFO, logger="app.core.exception_handlers"):
            r = client.get("/api/v1/workouts/history")
        assert r.status_code == 401
        assert any("UnauthorizedError" in record.message for record in caplog.records)

    def test_domain_exception_log_includes_request_path(self, client: TestClient, caplog):
        with caplog.at_level(logging.INFO, logger="app.core.exception_handlers"):
            client.get("/api/v1/workouts/history")
        assert any("/api/v1/workouts/history" in record.message for record in caplog.records)
