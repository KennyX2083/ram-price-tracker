from datetime import datetime, timezone
from decimal import Decimal

from alert_rules import AlertEvaluator
from config import Settings
from database import Database
from deal_processor import DealProcessor
from models import Listing


class FakeNotifier:
    def __init__(self) -> None:
        self.sent_alerts: list[dict[str, object]] = []

    def send_deal_alert(
        self,
        listing: Listing,
        reasons: list[str],
        average_30d: str | None = None,
        percent_below_average: str | None = None,
    ) -> None:
        self.sent_alerts.append({
            "listing": listing,
            "reasons": reasons,
            "average_30d": average_30d,
            "percent_below_average": (
                percent_below_average
            ),
        })


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
    )


def make_listing(
    price: str,
    *,
    listing_id: str = "test:deal-processor",
    name: str = (
        "Crucial 32GB (2 x 16GB) DDR5-5600 "
        "SODIMM Laptop Memory Kit"
    ),
) -> Listing:
    return Listing(
        listing_id=listing_id,
        retailer="Micro Center",
        seller="Micro Center",
        name=name,
        price=Decimal(price),
        url="https://example.com/product",
        in_stock=True,
        checked_at=datetime.now(timezone.utc),
    )


def build_processor(
    database_path: str,
) -> tuple[
    DealProcessor,
    Database,
    FakeNotifier,
]:
    settings = make_settings(database_path)

    database = Database(database_path)
    database.initialize()

    evaluator = AlertEvaluator(
        database=database,
        settings=settings,
    )

    notifier = FakeNotifier()

    processor = DealProcessor(
        database=database,
        evaluator=evaluator,
        notifier=notifier,
    )

    return processor, database, notifier


def test_first_observation_does_not_notify(
    tmp_path,
) -> None:
    database_path = str(
        tmp_path / "processor.db"
    )

    processor, database, notifier = (
        build_processor(database_path)
    )

    processor.process(
        make_listing("289.99")
    )

    assert notifier.sent_alerts == []

    assert database.get_observation_count(
        "test:deal-processor"
    ) == 1


def test_crossing_below_threshold_notifies_once(
    tmp_path,
) -> None:
    database_path = str(
        tmp_path / "processor.db"
    )

    processor, database, notifier = (
        build_processor(database_path)
    )

    processor.process(
        make_listing("329.99")
    )

    processor.process(
        make_listing("289.99")
    )

    processor.process(
        make_listing("279.99")
    )

    assert len(notifier.sent_alerts) == 1

    sent_alert = notifier.sent_alerts[0]

    assert sent_alert["listing"].price == Decimal(
        "289.99"
    )

    assert any(
        "Price crossed below" in reason
        for reason in sent_alert["reasons"]
    )

    assert database.get_observation_count(
        "test:deal-processor"
    ) == 3


def test_non_matching_ram_is_skipped(
    tmp_path,
) -> None:
    database_path = str(
        tmp_path / "processor.db"
    )

    processor, database, notifier = (
        build_processor(database_path)
    )

    invalid_listing = make_listing(
        "99.99",
        listing_id="test:invalid-ram",
        name=(
            "Crucial 32GB DDR5-5600 "
            "Desktop DIMM Memory"
        ),
    )

    processor.process(invalid_listing)

    assert notifier.sent_alerts == []

    assert database.get_observation_count(
        "test:invalid-ram"
    ) == 0