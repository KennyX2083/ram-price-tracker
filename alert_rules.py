from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from config import Settings
from database import Database
from models import Listing


@dataclass(frozen=True)
class AlertDecision:
    should_alert: bool
    reasons: list[str]

    average_30d: Decimal | None
    percent_below_average: Decimal | None

    below_price_threshold: bool
    below_average_threshold: bool


class AlertEvaluator:
    def __init__(
        self,
        database: Database,
        settings: Settings,
    ) -> None:
        self.database = database
        self.settings = settings

    def evaluate(
        self,
        listing: Listing,
    ) -> AlertDecision:
        state = self.database.get_alert_state(
            listing.listing_id
        )

        observation_count_total = (
            self.database.get_observation_count(
                listing.listing_id
            )
        )

        is_first_observation = (
            observation_count_total == 0
        )

        average_30d, observation_count, distinct_days = (
            self.database.get_30_day_statistics(
                listing.listing_id
            )
        )

        previously_below_price = bool(
            state["below_price_threshold"]
        )

        previously_below_average = bool(
            state["below_average_threshold"]
        )

        currently_below_price = (
            listing.price < self.settings.max_price
        )

        enough_average_history = (
            average_30d is not None
            and observation_count
            >= self.settings.minimum_history_observations
            and distinct_days
            >= self.settings.minimum_history_days
        )

        average_threshold: Decimal | None = None
        percent_below_average: Decimal | None = None
        currently_below_average = False

        if enough_average_history and average_30d is not None:
            average_threshold = (
                average_30d
                * (
                    Decimal("1")
                    - self.settings.discount_threshold
                )
            )

            currently_below_average = (
                listing.price < average_threshold
            )

            if average_30d > Decimal("0"):
                percent_below_average = (
                    average_30d - listing.price
                ) / average_30d

        crossed_price_threshold = (
            not is_first_observation
            and currently_below_price
            and not previously_below_price
        )

        crossed_average_threshold = (
            not is_first_observation
            and currently_below_average
            and not previously_below_average
        )

        reasons: list[str] = []

        if crossed_price_threshold:
            reasons.append(
                f"Price crossed below "
                f"${self.settings.max_price:.2f}"
            )

        if crossed_average_threshold:
            discount_percent = (
                self.settings.discount_threshold
                * Decimal("100")
            )

            reasons.append(
                f"Price crossed below "
                f"{discount_percent:.0f}% under its "
                f"30-day average"
            )

        cooldown_active = self._cooldown_active(
            state["last_alerted_at"]
        )

        should_alert = (
            bool(reasons)
            and listing.in_stock
            and not cooldown_active
        )

        return AlertDecision(
            should_alert=should_alert,
            reasons=reasons,
            average_30d=average_30d,
            percent_below_average=percent_below_average,
            below_price_threshold=currently_below_price,
            below_average_threshold=currently_below_average,
        )

    def update_state(
        self,
        listing: Listing,
        decision: AlertDecision,
    ) -> None:
        self.database.update_alert_state(
            listing_id=listing.listing_id,
            below_price_threshold=(
                decision.below_price_threshold
            ),
            below_average_threshold=(
                decision.below_average_threshold
            ),
        )

    def _cooldown_active(
        self,
        last_alerted_at: str | None,
    ) -> bool:
        if last_alerted_at is None:
            return False

        last_alerted = datetime.fromisoformat(
            last_alerted_at
        )

        if last_alerted.tzinfo is None:
            last_alerted = last_alerted.replace(
                tzinfo=timezone.utc
            )

        cooldown_ends = last_alerted + timedelta(
            hours=self.settings.alert_cooldown_hours
        )

        return datetime.now(timezone.utc) < cooldown_ends