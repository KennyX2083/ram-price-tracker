from datetime import datetime, timezone
from decimal import Decimal

from database import Database
from models import Listing


def make_listing(
    price: str,
) -> Listing:
    return Listing(
        listing_id="test:database",
        retailer="Test Retailer",
        seller="Test Retailer",
        name="Test DDR5 Laptop Memory",
        price=Decimal(price),
        url="https://example.com/database-test",
        in_stock=True,
        checked_at=datetime.now(timezone.utc),
    )


def test_register_listing_does_not_save_price(
    tmp_path,
) -> None:
    database_path = str(
        tmp_path / "database.db"
    )

    database = Database(database_path)
    database.initialize()

    listing = make_listing("299.99")

    database.register_listing(listing)

    assert (
        database.get_observation_count(
            listing.listing_id
        )
        == 0
    )


def test_save_price_observation_adds_history(
    tmp_path,
) -> None:
    database_path = str(
        tmp_path / "database.db"
    )

    database = Database(database_path)
    database.initialize()

    listing = make_listing("299.99")

    database.register_listing(listing)
    database.save_price_observation(listing)

    assert (
        database.get_observation_count(
            listing.listing_id
        )
        == 1
    )