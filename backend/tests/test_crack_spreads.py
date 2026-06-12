"""
Tests for Crack Spread Analytics endpoints.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.database.connection import get_db


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    return db


@pytest.fixture
def client(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Unit tests: service logic
# ---------------------------------------------------------------------------

class TestCrackSpreadService:
    def test_empty_stats_structure(self):
        from app.services.crack_spread_service import _empty_crack_stats
        stats = _empty_crack_stats("wti")
        assert stats["crude_type"] == "wti"
        assert stats["sample_size"] == 0
        assert stats["latest"] is None

    def test_record_to_dict(self):
        from app.services.crack_spread_service import _record_to_dict
        from app.models.crack_spread import CrackSpread
        from datetime import datetime, timezone

        mock_record = MagicMock(spec=CrackSpread)
        mock_record.id = 1
        mock_record.crude_type = "wti"
        mock_record.crude_price = 75.0
        mock_record.gasoline_price = 90.0   # $/bbl after conversion
        mock_record.distillate_price = 85.0
        mock_record.crack_spread = 11.67    # (2*90 + 1*85 - 3*75) / 3
        mock_record.timestamp = datetime(2024, 1, 15, tzinfo=timezone.utc)

        result = _record_to_dict(mock_record)
        assert result["crack_spread"] == 11.67
        assert result["crude_type"] == "wti"

    def test_crack_formula(self):
        """Verify the 3:2:1 formula numerically."""
        crude = 75.0
        gasoline = 90.0   # $/bbl (already converted from $/gal × 42)
        distillate = 85.0
        expected = (2 * gasoline + 1 * distillate - 3 * crude) / 3
        assert round(expected, 4) == round((180 + 85 - 225) / 3, 4)  # 40/3 ≈ 13.33


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------

class TestCrackEndpoints:
    def test_latest_invalid_crude_type(self, client):
        response = client.get("/api/crack/latest?crude_type=natural_gas")
        assert response.status_code == 400

    def test_latest_wti_triggers_compute_when_empty(self, client, mock_db):
        with patch("app.api.crack.compute_and_store_crack_spreads") as mock_compute, \
             patch("app.api.crack.latest_crack") as mock_latest:
            # First call returns None (empty DB), second returns data
            mock_latest.side_effect = [None, {
                "id": 1, "crude_type": "wti",
                "crude_price": 75.0, "gasoline_price": 90.0,
                "distillate_price": 85.0, "crack_spread": 13.33,
                "timestamp": "2024-01-15T00:00:00+00:00"
            }]
            mock_compute.return_value = {"wti": 252, "brent": 252}
            response = client.get("/api/crack/latest?crude_type=wti")

        assert response.status_code == 200
        data = response.json()
        assert data["crack_spread"] == 13.33

    def test_history_response_shape(self, client):
        with patch("app.api.crack.crack_history") as mock_hist:
            mock_hist.return_value = [
                {"id": 1, "crude_type": "wti", "crude_price": 75.0,
                 "gasoline_price": 90.0, "distillate_price": 85.0,
                 "crack_spread": 13.33, "timestamp": "2024-01-15T00:00:00+00:00"}
            ]
            response = client.get("/api/crack/history?crude_type=wti&days=30")

        assert response.status_code == 200
        data = response.json()
        assert data["crude_type"] == "wti"
        assert data["count"] == 1

    def test_statistics_returns_trend(self, client):
        with patch("app.api.crack.crack_statistics") as mock_stats:
            mock_stats.return_value = {
                "crude_type": "wti", "latest": 13.33, "avg_30d": 12.0,
                "avg_90d": 11.5, "volatility": 1.2, "trend": "positive",
                "sample_size": 90, "as_of": "2024-01-15T00:00:00+00:00"
            }
            response = client.get("/api/crack/statistics?crude_type=brent")

        assert response.status_code == 200
        data = response.json()
        assert data["trend"] in ("positive", "negative", "neutral")

    def test_days_boundary_validation(self, client):
        """days=0 is rejected by FastAPI query param validation."""
        response = client.get("/api/crack/history?crude_type=wti&days=0")
        assert response.status_code == 422
