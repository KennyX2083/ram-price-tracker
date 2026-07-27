from __future__ import annotations

import requests

from models import Listing


class DiscordNotifier:
    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    def send_test_message(self) -> None:
        payload = {
            "username": "RAM Deal Tracker",
            "content": (
                "RAM Deal Tracker is connected successfully."
            ),
        }

        self._send(payload)

    def send_deal_alert(
        self,
        listing: Listing,
        reasons: list[str],
        average_30d: str | None = None,
        percent_below_average: str | None = None,
    ) -> None:
        fields = [
            {
                "name": "Current price",
                "value": f"${listing.price:.2f}",
                "inline": True,
            },
            {
                "name": "Retailer",
                "value": listing.retailer,
                "inline": True,
            },
            {
                "name": "Seller",
                "value": listing.seller,
                "inline": True,
            },
        ]

        if average_30d is not None:
            fields.append({
                "name": "30-day average",
                "value": average_30d,
                "inline": True,
            })

        if percent_below_average is not None:
            fields.append({
                "name": "Below average",
                "value": percent_below_average,
                "inline": True,
            })

        fields.append({
            "name": "Alert reason",
            "value": "\n".join(
                f"• {reason}" for reason in reasons
            ),
            "inline": False,
        })

        embed: dict[str, object] = {
            "title": "DDR5-5600 2×16GB SODIMM deal",
            "description": listing.name,
            "url": listing.url,
            "fields": fields,
            "footer": {
                "text": (
                    "RAM Deal Tracker • "
                    "24-hour duplicate cooldown"
                )
            },
        }

        if listing.image_url:
            embed["thumbnail"] = {
                "url": listing.image_url
            }

        payload = {
            "username": "RAM Deal Tracker",
            "embeds": [embed],
        }

        self._send(payload)

    def _send(self, payload: dict[str, object]) -> None:
        response = requests.post(
            self.webhook_url,
            json=payload,
            timeout=15,
        )

        response.raise_for_status()