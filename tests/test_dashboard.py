from datetime import datetime, timezone
from decimal import Decimal

import pytest

from dashboard.app import app
from database import Database
from models import Listing


@pytest.fixture
def dashboard_database(
    tmp_path,
    monkeypatch,
):
    database_path = str(
        tmp_path / "dashboard_test.db"
    )

    database = Database(
        database_path
    )

    database.initialize()

    listing = Listing(
        listing_id="test:ram1",
        retailer="Test Retailer",
        seller="Test Retailer",
        name=(
            "Test 32GB 2x16GB "
            "DDR5-5600 SODIMM"
        ),
        price=Decimal("199.99"),
        url="https://example.com/ram",
        in_stock=True,
        checked_at=datetime.now(
            timezone.utc
        ),
        brand="TestBrand",
        model_number="TEST123",
    )

    database.register_listing(
        listing
    )

    database.save_price_observation(
        listing
    )

    monkeypatch.setattr(
        "dashboard.app.database",
        database,
    )

    return database


@pytest.fixture
def client(
    dashboard_database,
):
    app.config.update(
        TESTING=True
    )

    with app.test_client() as client:
        yield client


def test_dashboard_index(
    client,
) -> None:
    response = client.get("/")

    assert response.status_code == 200

    assert b"RAM Deal Tracker" in (
        response.data
    )


def test_product_detail(
    client,
) -> None:
    response = client.get(
        "/product/test:ram1"
    )

    assert response.status_code == 200

    assert b"Test 32GB" in (
        response.data
    )


def test_missing_product_returns_404(
    client,
) -> None:
    response = client.get(
        "/product/does-not-exist"
    )

    assert response.status_code == 404