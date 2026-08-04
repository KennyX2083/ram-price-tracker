from datetime import datetime, timezone
from decimal import Decimal
from alert_rules import AlertEvaluator
from config import Settings
from database import Database
from models import Listing


def make_listing(
    price: str,
    listing_id: str = "test:alert-flow",
) -> Listing:
    return Listing(
        listing_id=listing_id,
        retailer="Test Retailer",
        seller="Test Retailer",
        name=(
            "Test 32GB 2x16GB DDR5-5600 "
            "SODIMM Laptop Memory"
        ),
        price=Decimal(price),
        url="https://example.com/test",
        in_stock=True,
        checked_at=datetime.now(timezone.utc),
    )


def make_settings(
    database_path: str,
) -> Settings:
    return Settings(
        database_path=database_path,
        discord_webhook_url="",
        best_buy_api_key="",
        microcenter_product_urls=(),
        max_price=Decimal("300.00"),
        discount_threshold=Decimal("0.20"),
        minimum_history_observations=3,
        minimum_history_days=1,
        alert_cooldown_hours=24,
        amazon_credential_id="",
        amazon_credential_secret="",
        amazon_partner_tag="",
        amazon_marketplace="www.amazon.com",
    )


def evaluate_and_save(
    database: Database,
    evaluator: AlertEvaluator,
    listing: Listing,
):
    database.register_listing(listing)

    decision = evaluator.evaluate(listing)

    database.save_price_observation(listing)
    evaluator.update_state(listing, decision)

    return decision


def test_first_observation_does_not_alert(
    tmp_path,
) -> None:
    database_path = str(
        tmp_path / "test_prices.db"
    )

    settings = make_settings(database_path)
    database = Database(database_path)
    database.initialize()

    evaluator = AlertEvaluator(
        database=database,
        settings=settings,
    )

    decision = evaluate_and_save(
        database,
        evaluator,
        make_listing("289.99"),
    )

    assert decision.should_alert is False
    assert decision.reasons == []


def test_crossing_below_price_threshold_alerts(
    tmp_path,
) -> None:
    database_path = str(
        tmp_path / "test_prices.db"
    )

    settings = make_settings(database_path)
    database = Database(database_path)
    database.initialize()

    evaluator = AlertEvaluator(
        database=database,
        settings=settings,
    )

    first = evaluate_and_save(
        database,
        evaluator,
        make_listing("289.99"),
    )

    above = evaluate_and_save(
        database,
        evaluator,
        make_listing("329.99"),
    )

    crossing = evaluate_and_save(
        database,
        evaluator,
        make_listing("289.99"),
    )

    remaining_below = evaluate_and_save(
        database,
        evaluator,
        make_listing("279.99"),
    )

    assert first.should_alert is False
    assert above.should_alert is False

    assert crossing.should_alert is True
    assert any(
        "Price crossed below" in reason
        for reason in crossing.reasons
    )

    assert remaining_below.should_alert is False