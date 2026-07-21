"""Tests for the shared expiration-risk classifier.

fefo_engine.py, inventory_service.py, and dashboard_service.py previously
each reimplemented these same 30/60/90-day boundaries independently.
"""
import pytest

from app.services.expiration_classifier import classify_expiration


@pytest.mark.parametrize(
    "days,expected",
    [
        (-5, "expired"),
        (0, "expired"),
        (1, "critical"),
        (30, "critical"),
        (31, "warning"),
        (60, "warning"),
        (61, "caution"),
        (90, "caution"),
        (91, "safe"),
        (1000, "safe"),
    ],
)
def test_classify_expiration_boundaries(days, expected):
    assert classify_expiration(days) == expected
