from __future__ import annotations
from alert_rules import AlertEvaluator
from database import Database
from discord_alerts import DiscordNotifier
from filters import enrich_from_name, matches_requirements
from models import Listing


class DealProcessor:
    def __init__(
        self,
        database: Database,
        evaluator: AlertEvaluator,
        notifier: DiscordNotifier,
    ) -> None:
        self.database = database
        self.evaluator = evaluator
        self.notifier = notifier

    def process(self, listing: Listing) -> None:
        listing = enrich_from_name(listing)

        if not matches_requirements(listing):
            print(
                f"Skipped non-matching listing: "
                f"{listing.name}"
            )
            return

        # Save the current observation before calculating
        # rolling statistics.
        self.database.register_listing(listing)

        decision = self.evaluator.evaluate(listing)

        print(
            f"{listing.retailer}: {listing.name} "
            f"- ${listing.price:.2f}"
        )

        if decision.should_alert:
            self.notifier.send_deal_alert(
                listing=listing,
                reasons=decision.reasons,
                average_30d=(
                    f"${decision.average_30d:.2f}"
                    if decision.average_30d is not None
                    else None
                ),
                percent_below_average=(
                    f"{decision.percent_below_average:.1%}"
                    if decision.percent_below_average
                    is not None
                    else None
                ),
            )

            self.database.record_alert(
                listing_id=listing.listing_id,
                price=listing.price,
                average_30d=decision.average_30d,
                reason="; ".join(decision.reasons),
            )

            print("Discord deal alert sent.")
        else:
            print("No alert triggered.")

        # Save price after evalutating against previous history
        self.database.save_price_observation(listing)

        # Always update crossing state after evaluation.
        self.evaluator.update_state(
            listing,
            decision,
        )   