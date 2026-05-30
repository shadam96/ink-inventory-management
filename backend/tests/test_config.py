"""Tests for database URL normalization in app.core.config."""
import logging

import pytest

from app.core.config import normalize_database_url


class TestNormalizeDatabaseUrl:
    """Tests for the pure-function URL normalizer.

    Covers the failures we've hit pasting Neon URLs into Railway: asyncpg's
    URL parser only accepts a small allowlist of query params, and libpq's
    full set (``sslmode``, ``channel_binding``, ``application_name``, …)
    becomes an "unknown kwarg" TypeError at connect time. The normalizer
    rewrites ``sslmode`` and drops everything else asyncpg doesn't accept.
    """

    def test_empty_string_passes_through(self):
        assert normalize_database_url("") == ""

    def test_swaps_scheme_to_asyncpg(self):
        url = "postgresql://user:pwd@host/db"
        assert normalize_database_url(url) == "postgresql+asyncpg://user:pwd@host/db"

    def test_leaves_asyncpg_scheme_alone(self):
        url = "postgresql+asyncpg://user:pwd@host/db"
        assert normalize_database_url(url) == url

    def test_rewrites_sslmode_to_ssl(self):
        url = "postgresql://user:pwd@host/db?sslmode=require"
        assert (
            normalize_database_url(url)
            == "postgresql+asyncpg://user:pwd@host/db?ssl=require"
        )

    def test_leaves_ssl_param_alone(self):
        url = "postgresql://user:pwd@host/db?ssl=require"
        assert (
            normalize_database_url(url)
            == "postgresql+asyncpg://user:pwd@host/db?ssl=require"
        )

    def test_no_query_string_no_changes_beyond_scheme(self):
        url = "postgresql://user:pwd@host:5432/db"
        assert (
            normalize_database_url(url)
            == "postgresql+asyncpg://user:pwd@host:5432/db"
        )

    def test_translates_non_require_sslmode_values(self):
        url = "postgresql://u:p@h/d?sslmode=disable"
        assert normalize_database_url(url).endswith("?ssl=disable")

    def test_preserves_target_session_attrs(self):
        """target_session_attrs is one of the few non-ssl params asyncpg accepts."""
        url = "postgresql://u:p@h/d?sslmode=require&target_session_attrs=read-write"
        result = normalize_database_url(url)
        assert "ssl=require" in result
        assert "target_session_attrs=read-write" in result

    @pytest.mark.parametrize(
        "param",
        [
            "channel_binding",       # the second failure we hit
            "application_name",      # commonly added by tooling
            "connect_timeout",       # libpq-specific name (asyncpg uses `timeout`)
            "options",
            "gssencmode",
            "keepalives_idle",
            "sslrootcert",
        ],
    )
    def test_drops_libpq_only_param(self, param):
        """Any libpq param not in the asyncpg allowlist is silently dropped."""
        url = f"postgresql://u:p@h/d?{param}=anything"
        result = normalize_database_url(url)
        assert param not in result

    def test_full_neon_style_url_round_trip(self):
        """End-to-end: the exact shape Neon hands out today comes out clean."""
        url = "postgresql://user:pwd@ep-x.region.aws.neon.tech/db?sslmode=require&channel_binding=require"
        result = normalize_database_url(url)
        assert result == (
            "postgresql+asyncpg://user:pwd@ep-x.region.aws.neon.tech/db?ssl=require"
        )

    def test_logs_warning_when_dropping_params(self, caplog):
        """Operators get a breadcrumb when their config has something we couldn't pass through."""
        with caplog.at_level(logging.WARNING, logger="app.core.config"):
            normalize_database_url(
                "postgresql://u:p@h/d?sslmode=require&channel_binding=require&options=-c+foo"
            )
        assert any(
            "channel_binding" in r.message and "options" in r.message
            for r in caplog.records
        )
