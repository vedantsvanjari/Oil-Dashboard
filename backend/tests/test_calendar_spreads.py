"""
Tests for Calendar Spread Analytics endpoints.
Uses FastAPI TestClient — does not require a live PostgreSQL connection.
Database is stubbed via dependency override.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.database.connection import get_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    """Return a MagicMock that satisfies the Session interface."""
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    return db


@pytest.fixture
def client(mock_db):
    """FastAPI test client with database dependency overridden."""
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Unit tests: service logic
# ---------------------------------------------------------------------------

class TestCalendarSpreadService:
    def test_empty_stats_structure(self):
        from app.services.calendar_spread_service import _empty_stats
        stats = _empty_stats()
        assert stats["sample_size"] == 0
        assert stats["latest"] is None
        assert stats["z_score"] is None

    def test_record_to_dict(self):
        from app.services.calendar_spread_service import _record_to_dict
        from app.models.calendar_spread import CalendarSpread
        from datetime import datetime, timezone

        mock_record = MagicMock(spec=CalendarSpread)
        mock_record.id = 1
        mock_record.commodity = "wti"
        mock_record.contract1 = "M1"
        mock_record.contract2 = "M2"
        mock_record.price1 = 75.0
        mock_record.price2 = 74.5
        mock_record.spread = 0.5
        mock_record.timestamp = datetime(2024, 1, 15, tzinfo=timezone.utc)

        result = _record_to_dict(mock_record)
        assert result["spread"] == 0.5
        assert result["commodity"] == "wti"
        assert "timestamp" in result

    def test_spread_statistics_with_data(self):
        """Statistics function returns correct structure when records exist."""
        from app.services.calendar_spread_service import spread_statistics
        from app.models.calendar_spread import CalendarSpread
        from datetime import datetime, timezone

        mock_record = MagicMock(spec=CalendarSpread)
        mock_record.spread = 0.5
        mock_record.timestamp = datetime(2024, 1, 15, tzinfo=timezone.utc)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            mock_record
        ]

        stats = spread_statistics(mock_db, "wti", "M1", "M2")
        assert stats["latest"] == 0.5
        assert stats["sample_size"] == 1
        assert "volatility" in stats
        assert "z_score" in stats


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------

class TestSpreadsEndpoints:
    def test_brent_wti_legacy_route(self, client, mock_db):
        """Legacy /brent-wti route must still respond."""
        with patch("app.api.spreads.get_brent_wti_spread") as mock_svc:
            mock_svc.return_value = {
                "current_spread": 1.5,
                "previous_spread": 1.3,
                "daily_change": 0.2,
                "history": [],
            }
            response = client.get("/api/spreads/brent-wti")
        assert response.status_code == 200
        data = response.json()
        assert "current_spread" in data

    def test_latest_spread_invalid_commodity(self, client):
        response = client.get("/api/spreads/latest?commodity=invalid&contract1=M1&contract2=M2")
        assert response.status_code == 400

    def test_latest_spread_invalid_contract(self, client):
        response = client.get("/api/spreads/latest?commodity=wti&contract1=XX&contract2=M2")
        assert response.status_code == 400

    def test_statistics_returns_empty_stats_when_no_data(self, client, mock_db):
        """Statistics endpoint must return valid structure even with empty DB."""
        with patch("app.api.spreads.compute_and_store_calendar_spreads") as mock_compute, \
             patch("app.api.spreads.spread_statistics") as mock_stats:
            mock_compute.return_value = {}
            mock_stats.return_value = {
                "commodity": "wti", "contract1": "M1", "contract2": "M2",
                "latest": None, "daily_change": None, "weekly_change": None,
                "monthly_change": None, "volatility": None, "z_score": None,
                "sample_size": 0, "as_of": None
            }
            response = client.get("/api/spreads/statistics?commodity=wti&contract1=M1&contract2=M2")

        assert response.status_code == 200
        data = response.json()
        assert "sample_size" in data

    def test_history_returns_correct_shape(self, client, mock_db):
        with patch("app.api.spreads.spread_history") as mock_hist:
            mock_hist.return_value = [
                {"id": 1, "commodity": "wti", "contract1": "M1", "contract2": "M2",
                 "price1": 75.0, "price2": 74.5, "spread": 0.5, "timestamp": "2024-01-15T00:00:00+00:00"}
            ]
            response = client.get("/api/spreads/history?commodity=wti&contract1=M1&contract2=M2&days=30")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["commodity"] == "wti"
        assert len(data["history"]) == 1

    def test_valid_windows_for_days_param(self, client):
        """days=0 should be rejected (ge=1 constraint)."""
        response = client.get("/api/spreads/history?days=0")
        assert response.status_code == 422  # FastAPI validation error
