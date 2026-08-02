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

def test_get_latest_prices_returns_one_row_per_listing(
    tmp_path,
) -> None:
    database_path = str(
        tmp_path / "latest-prices.db"
    )

    database = Database(database_path)
    database.initialize()

    first_listing = make_listing("429.99")

    database.register_listing(first_listing)
    database.save_price_observation(first_listing)

    updated_listing = Listing(
        listing_id=first_listing.listing_id,
        retailer=first_listing.retailer,
        seller=first_listing.seller,
        name=first_listing.name,
        price=Decimal("399.99"),
        url=first_listing.url,
        in_stock=True,
        checked_at=datetime.now(timezone.utc),
    )

    database.register_listing(updated_listing)
    database.save_price_observation(
        updated_listing
    )

    latest_prices = database.get_latest_prices()

    assert len(latest_prices) == 1
    assert latest_prices[0].listing_id == (
        first_listing.listing_id
    )
    assert latest_prices[0].price == Decimal(
        "399.99"
    )

def test_get_latest_price_returns_newest_observation(
    tmp_path,
) -> None:
    database_path = str(
        tmp_path / "latest-price.db"
    )

    database = Database(database_path)
    database.initialize()

    listing = make_listing("429.99")

    database.register_listing(listing)
    database.save_price_observation(listing)

    updated_listing = Listing(
        listing_id=listing.listing_id,
        retailer=listing.retailer,
        seller=listing.seller,
        name=listing.name,
        price=Decimal("379.99"),
        url=listing.url,
        in_stock=True,
        checked_at=datetime.now(timezone.utc),
    )

    database.register_listing(updated_listing)
    database.save_price_observation(
        updated_listing
    )

    latest = database.get_latest_price(
        listing.listing_id
    )

    assert latest is not None
    assert latest.price == Decimal("379.99")