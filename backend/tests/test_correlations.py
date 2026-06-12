"""
Tests for Advanced Correlation Engine endpoints.
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.database.connection import get_db


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.query.return_value.distinct.return_value.all.return_value = []
    db.query.return_value.count.return_value = 0
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

class TestCorrelationService:
    def test_valid_windows_constant(self):
        from app.services.correlation_service import VALID_WINDOWS
        assert "7D" in VALID_WINDOWS
        assert "30D" in VALID_WINDOWS
        assert "90D" in VALID_WINDOWS
        assert "180D" in VALID_WINDOWS
        assert VALID_WINDOWS["30D"] == 30

    def test_matrix_groups_complete(self):
        from app.services.correlation_service import MATRIX_GROUPS
        assert "product" in MATRIX_GROUPS
        assert "spread" in MATRIX_GROUPS
        assert "macro" in MATRIX_GROUPS
        assert "inventory" in MATRIX_GROUPS

    def test_pearson_matrix_computation(self):
        """Test the internal matrix computation with synthetic data."""
        import pandas as pd
        import numpy as np
        from app.services.correlation_service import _compute_pearson_matrix

        # Create perfectly correlated series
        dates = pd.date_range("2024-01-01", periods=50)
        df = pd.DataFrame({
            "asset_a": range(50),
            "asset_b": range(50),      # Perfect positive correlation
            "asset_c": range(49, -1, -1),  # Perfect negative correlation
        }, index=dates)

        labels, matrix = _compute_pearson_matrix(df, ["asset_a", "asset_b", "asset_c"])

        assert "asset_a" in labels
        assert len(matrix) == 3
        # a-b should be 1.0
        a_idx = labels.index("asset_a")
        b_idx = labels.index("asset_b")
        c_idx = labels.index("asset_c")
        assert matrix[a_idx][b_idx] == 1.0
        assert matrix[a_idx][c_idx] == -1.0

    def test_align_series_handles_different_frequencies(self):
        """Weekly series should be forward-filled to daily."""
        import pandas as pd
        from app.services.correlation_service import _align_series

        # Daily series
        daily_idx = pd.date_range("2024-01-01", periods=30, freq="D")
        daily = pd.Series(range(30), index=daily_idx, name="daily_asset")

        # Weekly series (only 4-5 points)
        weekly_idx = pd.date_range("2024-01-01", periods=5, freq="7D")
        weekly = pd.Series(range(5), index=weekly_idx, name="weekly_asset")

        df = _align_series({"daily_asset": daily, "weekly_asset": weekly})

        # Both columns should be present
        assert "daily_asset" in df.columns
        assert "weekly_asset" in df.columns
        # After ffill, weekly NaNs should be filled (allowing some at the end)
        assert df["weekly_asset"].notna().sum() >= 5

    def test_discover_datasets_empty_db(self):
        """discover_datasets must not crash on empty database."""
        from app.services.correlation_service import discover_datasets

        mock_db = MagicMock()
        mock_db.query.return_value.distinct.return_value.all.return_value = []
        mock_db.query.return_value.count.return_value = 0

        datasets = discover_datasets(mock_db)
        # Should include at least the yfinance-only sources
        names = [d["name"] for d in datasets]
        assert "vix" in names
        assert "sp500" in names


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------

class TestCorrelationEndpoints:
    def test_datasets_endpoint_returns_categories(self, client, mock_db):
        with patch("app.api.correlations.discover_datasets") as mock_disc:
            mock_disc.return_value = [
                {"name": "wti", "category": "energy", "source": "prices_table", "description": "WTI"},
                {"name": "vix", "category": "macro", "source": "yfinance_live", "description": "VIX"},
            ]
            response = client.get("/api/correlations/datasets")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert "energy" in data["categories"] or "macro" in data["categories"]

    def test_matrix_invalid_window(self, client):
        response = client.get("/api/correlations/matrix?window=INVALID&matrix_type=product")
        assert response.status_code == 400

    def test_matrix_invalid_type(self, client):
        response = client.get("/api/correlations/matrix?window=30D&matrix_type=unknown")
        assert response.status_code == 400

    def test_matrix_valid_response_shape(self, client):
        with patch("app.api.correlations.get_matrix") as mock_matrix:
            mock_matrix.return_value = {
                "window": "30D",
                "matrix_type": "product",
                "labels": ["brent", "wti", "dxy"],
                "matrix": [
                    [1.0, 0.98, -0.65],
                    [0.98, 1.0, -0.62],
                    [-0.65, -0.62, 1.0],
                ],
                "computed_at": "2024-01-15T00:00:00+00:00",
                "cached": False,
            }
            response = client.get("/api/correlations/matrix?window=30D&matrix_type=product")

        assert response.status_code == 200
        data = response.json()
        assert data["window"] == "30D"
        assert len(data["labels"]) == 3
        assert len(data["matrix"]) == 3
        assert len(data["matrix"][0]) == 3
        # Diagonal should be 1.0
        for i in range(3):
            assert data["matrix"][i][i] == 1.0

    def test_top_positive_response_shape(self, client):
        with patch("app.api.correlations.get_top_correlations") as mock_top:
            mock_top.return_value = [
                {"asset_1": "wti", "asset_2": "brent", "correlation": 0.98},
                {"asset_1": "gasoline", "asset_2": "wti", "correlation": 0.85},
            ]
            response = client.get("/api/correlations/top-positive?window=30D&n=10")

        assert response.status_code == 200
        data = response.json()
        assert data["direction"] == "positive"
        assert data["count"] == 2
        for pair in data["pairs"]:
            assert pair["correlation"] > 0

    def test_top_negative_response_shape(self, client):
        with patch("app.api.correlations.get_top_correlations") as mock_top:
            mock_top.return_value = [
                {"asset_1": "dxy", "asset_2": "brent", "correlation": -0.72},
            ]
            response = client.get("/api/correlations/top-negative?window=30D&n=5")

        assert response.status_code == 200
        data = response.json()
        assert data["direction"] == "negative"
        for pair in data["pairs"]:
            assert pair["correlation"] < 0

    def test_n_boundary_validation(self, client):
        """n=0 must be rejected (ge=1 FastAPI constraint)."""
        response = client.get("/api/correlations/top-positive?n=0")
        assert response.status_code == 422

    def test_force_refresh_param_accepted(self, client):
        with patch("app.api.correlations.get_matrix") as mock_matrix:
            mock_matrix.return_value = {
                "window": "7D", "matrix_type": "macro",
                "labels": ["wti"], "matrix": [[1.0]],
                "computed_at": "2024-01-15T00:00:00+00:00", "cached": False,
            }
            response = client.get(
                "/api/correlations/matrix?window=7D&matrix_type=macro&force_refresh=true"
            )
        assert response.status_code == 200
        # Verify force_refresh=True was passed through
        mock_matrix.assert_called_once()
        call_kwargs = mock_matrix.call_args.kwargs
        assert call_kwargs.get("force_refresh") is True
