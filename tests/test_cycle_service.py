"""
Unit tests for deterministic cycle prediction logic.
Run with: pytest tests/ -v
"""

from datetime import date, timedelta

import pytest

from app.services.cycle_service import (
    predict_next_period,
    days_until_next_period,
    is_cycle_related_query,
    format_date,
)
from app.utils.validators import parse_date_input, validate_period_date


class TestCyclePrediction:
    def test_default_28_day_cycle(self):
        last = date(2025, 3, 1)
        expected = date(2025, 3, 29)
        assert predict_next_period(last) == expected

    def test_custom_cycle_length(self):
        last = date(2025, 3, 1)
        assert predict_next_period(last, cycle_length_days=30) == date(2025, 3, 31)

    def test_days_until_future(self):
        future = date.today() + timedelta(days=5)
        assert days_until_next_period(future) == 5

    def test_days_until_past(self):
        past = date.today() - timedelta(days=3)
        assert days_until_next_period(past) == -3

    def test_format_date(self):
        d = date(2025, 3, 15)
        assert "15" in format_date(d)
        assert "2025" in format_date(d)


class TestCycleQueryClassifier:
    def test_cycle_related_queries(self):
        assert is_cycle_related_query("when is my next period?")
        assert is_cycle_related_query("cycle prediction")
        assert is_cycle_related_query("days until my period")
        assert is_cycle_related_query("my period tracker")

    def test_non_cycle_queries(self):
        assert not is_cycle_related_query("I have a headache")
        assert not is_cycle_related_query("what foods help with cramps?")
        assert not is_cycle_related_query("hello, how are you?")


class TestDateParser:
    def test_dd_mm_yyyy_dash(self):
        assert parse_date_input("15-03-2025") == date(2025, 3, 15)

    def test_dd_mm_yyyy_slash(self):
        assert parse_date_input("15/03/2025") == date(2025, 3, 15)

    def test_yyyy_mm_dd(self):
        assert parse_date_input("2025-03-15") == date(2025, 3, 15)

    def test_invalid_returns_none(self):
        assert parse_date_input("not a date") is None
        assert parse_date_input("32-13-2025") is None

    def test_future_date_fails_validation(self):
        future = date.today() + timedelta(days=1)
        d = parse_date_input(future.strftime("%d-%m-%Y"))
        assert d is not None
        error = validate_period_date(d)
        assert error == "future_date"

    def test_too_old_date_fails_validation(self):
        old = date.today() - timedelta(days=200)
        d = parse_date_input(old.strftime("%d-%m-%Y"))
        assert d is not None
        error = validate_period_date(d)
        assert error == "date_too_old"

    def test_valid_recent_date(self):
        valid = date.today() - timedelta(days=10)
        d = parse_date_input(valid.strftime("%d-%m-%Y"))
        assert d is not None
        assert validate_period_date(d) is None
