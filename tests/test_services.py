import json
from datetime import datetime, timedelta

import pytest

from app.services import build_chart_data, compute_quote_totals, days_since


class TestDaysSince:
    def test_today_returns_zero(self):
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        assert days_since(now) == 0

    def test_yesterday_returns_one(self):
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y %H:%M")
        assert days_since(yesterday) == 1

    def test_invalid_string_returns_zero(self):
        assert days_since("not-a-date") == 0

    def test_empty_string_returns_zero(self):
        assert days_since("") == 0


class TestComputeQuoteTotals:
    def test_no_discount_no_surcharge(self):
        items = [{"quantity": 2, "unit_price": 10.0}]
        result = compute_quote_totals(items, 0, 0)
        assert result["subtotal"] == 20.0
        assert result["surcharge_amt"] == 0.0
        assert result["discount_amt"] == 0.0
        assert result["total"] == 20.0

    def test_surcharge_applied_before_discount(self):
        # subtotal=100, surcharge 10% -> 110, discount 10% -> 99
        items = [{"quantity": 1, "unit_price": 100.0}]
        result = compute_quote_totals(items, discount_pct=10, surcharge_pct=10)
        assert result["subtotal"] == 100.0
        assert result["surcharge_amt"] == 10.0
        assert result["discount_amt"] == 11.0
        assert result["total"] == 99.0

    def test_discount_only(self):
        items = [{"quantity": 4, "unit_price": 25.0}]
        result = compute_quote_totals(items, discount_pct=20, surcharge_pct=0)
        assert result["subtotal"] == 100.0
        assert result["discount_amt"] == 20.0
        assert result["total"] == 80.0

    def test_empty_items(self):
        result = compute_quote_totals([], 0, 0)
        assert result["subtotal"] == 0.0
        assert result["total"] == 0.0

    def test_multiple_items(self):
        items = [
            {"quantity": 1, "unit_price": 50.0},
            {"quantity": 2, "unit_price": 25.0},
        ]
        result = compute_quote_totals(items, 0, 0)
        assert result["subtotal"] == 100.0
        assert result["total"] == 100.0

    def test_rounding(self):
        items = [{"quantity": 1, "unit_price": 10.0}]
        result = compute_quote_totals(items, discount_pct=3, surcharge_pct=0)
        assert result["discount_amt"] == 0.30
        assert result["total"] == 9.70


class TestBuildChartData:
    def setup_method(self):
        self.charts = build_chart_data(
            base_cost_per_unit=10.0,
            filament_cost=4.0,
            electricity_cost=2.0,
            depreciation_cost=1.0,
            other_costs=3.0,
            multiplier=2.0,
        )

    def test_returns_breakdown_and_profit_keys(self):
        assert "breakdown" in self.charts
        assert "profit" in self.charts

    def test_breakdown_is_valid_json(self):
        data = json.loads(self.charts["breakdown"])
        assert "labels" in data
        assert "datasets" in data

    def test_profit_is_valid_json(self):
        data = json.loads(self.charts["profit"])
        assert "labels" in data
        assert "datasets" in data

    def test_breakdown_has_five_datasets(self):
        data = json.loads(self.charts["breakdown"])
        assert len(data["datasets"]) == 5

    def test_custom_multiplier_included_in_labels(self):
        charts = build_chart_data(10, 4, 2, 1, 3, 3.5)
        data = json.loads(charts["breakdown"])
        assert "×3.5" in data["labels"]
