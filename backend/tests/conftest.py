"""
Pytest configuration and test isolation fixtures for StockPulse AI.
Enforces strict authentication defaults (Stage 12.2 Security Hardening)
while providing isolated legacy authentication support for Stage 1-9 tests.
"""
import pytest
from backend.app.core.config import settings
from backend.app.core.rate_limit import _MEMORY_STORE, _LOCK


@pytest.fixture(autouse=True)
def reset_rate_limit_store():
    """Resets in-memory auth rate limit store between test cases to prevent false 429s during test suites."""
    with _LOCK:
        _MEMORY_STORE.clear()
    yield
    with _LOCK:
        _MEMORY_STORE.clear()


LEGACY_TEST_MODULES = {
    "test_smart_alerts",
    "test_portfolio_risk",
    "test_events",
    "test_research",
    "test_news",
    "test_api",
    "test_ml",
    "test_predictive_engine",
    "test_database",
    "test_indicators",
}


@pytest.fixture(autouse=True)
def auth_isolation(request):
    """
    By default, tests run with strict production-like authentication settings:
    ALLOW_LEGACY_HEADER_AUTH = False and ALLOW_DEFAULT_USER_FALLBACK = False.

    For Stage 1-9 regression test modules that rely on X-User-Id header auth or
    anonymous default user fallback, legacy auth is isolated and enabled only
    for those specific modules or tests explicitly marked with @pytest.mark.legacy_auth.
    Security audit suites (test_security_*) ALWAYS run strictly with legacy auth disabled.
    """
    module_name = request.module.__name__.split(".")[-1] if request.module else ""
    is_security_module = "security" in module_name
    has_legacy_mark = request.node.get_closest_marker("legacy_auth") is not None
    is_legacy_module = module_name in LEGACY_TEST_MODULES

    orig_legacy = settings.ALLOW_LEGACY_HEADER_AUTH
    orig_fallback = settings.ALLOW_DEFAULT_USER_FALLBACK

    if (is_legacy_module or has_legacy_mark) and not is_security_module:
        settings.ALLOW_LEGACY_HEADER_AUTH = True
        settings.ALLOW_DEFAULT_USER_FALLBACK = True
    else:
        settings.ALLOW_LEGACY_HEADER_AUTH = False
        settings.ALLOW_DEFAULT_USER_FALLBACK = False

    yield

    settings.ALLOW_LEGACY_HEADER_AUTH = orig_legacy
    settings.ALLOW_DEFAULT_USER_FALLBACK = orig_fallback


@pytest.fixture
def legacy_auth():
    """Explicit fixture for individual test cases that specifically require legacy authentication."""
    orig_legacy = settings.ALLOW_LEGACY_HEADER_AUTH
    orig_fallback = settings.ALLOW_DEFAULT_USER_FALLBACK
    settings.ALLOW_LEGACY_HEADER_AUTH = True
    settings.ALLOW_DEFAULT_USER_FALLBACK = True
    yield
    settings.ALLOW_LEGACY_HEADER_AUTH = orig_legacy
    settings.ALLOW_DEFAULT_USER_FALLBACK = orig_fallback
