"""Tests for the Frankfurter FX-rate refresh job."""
from decimal import Decimal

import pytest

from app.tasks.scheduler import _invert_frankfurter_rates


class TestInvertFrankfurterRates:
    """Pure-function tests for the rate inversion logic.

    The full refresh job is an integration of httpx + DB + scheduler glue; the
    risky math (reciprocating Frankfurter's ILS-base quotes) is isolated here
    so it can be exercised without mocking either.
    """

    def test_inverts_typical_response(self):
        # Frankfurter: 1 ILS = 0.25 USD, 1 ILS = 0.20 EUR, 1 ILS = 8 TRY
        # Our store: 1 USD = 4 ILS, 1 EUR = 5 ILS, 1 TRY = 0.125 ILS
        payload = {
            "amount": 1.0,
            "base": "ILS",
            "date": "2026-05-29",
            "rates": {"USD": 0.25, "EUR": 0.20, "TRY": 8},
        }
        result = _invert_frankfurter_rates(payload)
        assert result is not None
        usd_to_ils, eur_to_ils, try_to_ils = result
        assert usd_to_ils == Decimal("4")
        assert eur_to_ils == Decimal("5")
        assert try_to_ils == Decimal("0.125")

    def test_returns_none_for_missing_rates_key(self):
        """Missing key means the upstream payload is malformed — refuse to overwrite."""
        assert _invert_frankfurter_rates({"base": "ILS"}) is None

    def test_returns_none_for_missing_currency(self):
        assert _invert_frankfurter_rates({"rates": {"USD": 0.25, "EUR": 0.20}}) is None

    def test_returns_none_for_zero_rate(self):
        """A zero rate would cause a division-by-zero and corrupt the DB row."""
        assert _invert_frankfurter_rates({"rates": {"USD": 0, "EUR": 0.20, "TRY": 8}}) is None

    def test_returns_none_for_negative_rate(self):
        assert _invert_frankfurter_rates({"rates": {"USD": -0.25, "EUR": 0.20, "TRY": 8}}) is None

    def test_returns_none_for_non_numeric_rate(self):
        assert _invert_frankfurter_rates({"rates": {"USD": "0.25", "EUR": 0.20, "TRY": 8}}) is None
