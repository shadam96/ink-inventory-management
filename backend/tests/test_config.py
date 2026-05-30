"""Tests for database URL normalization in app.core.config."""
from app.core.config import normalize_database_url


class TestNormalizeDatabaseUrl:
    """Tests for the pure-function URL normalizer.

    Covers the failure we hit in staging: Neon hands out connection strings
    with ``sslmode=require`` (psycopg2 syntax), but our backend uses asyncpg,
    which rejects that kwarg. The normalizer rewrites it transparently.
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

    def test_preserves_other_query_params_when_rewriting_ssl(self):
        url = "postgresql://u:p@h/d?sslmode=require&channel_binding=disable"
        assert (
            normalize_database_url(url)
            == "postgresql+asyncpg://u:p@h/d?ssl=require&channel_binding=disable"
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
        """asyncpg accepts the same value names — we only rewrite the key."""
        url = "postgresql://u:p@h/d?sslmode=disable"
        assert normalize_database_url(url).endswith("?ssl=disable")
