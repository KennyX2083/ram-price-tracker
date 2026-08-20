from __future__ import annotations
from flask import Flask, render_template, abort
from config import load_settings
from database import Database
from datetime import datetime

app = Flask(__name__)

settings = load_settings()

database = Database(
    settings.database_path
)

@app.template_filter("format_datetime")
def format_datetime(
    value: str | None,
) -> str:
    if not value:
        return "—"

    try:
        parsed = datetime.fromisoformat(
            value
        )

        return parsed.strftime(
            "%b %d, %Y %I:%M %p"
        )

    except ValueError:
        return value
    
@app.route("/")
def index():
    listings = (
        database.get_dashboard_listings()
    )

    alerts = database.get_recent_alerts(
        limit=10,
    )

    prices = [
        listing["current_price_cents"]
        for listing in listings
        if listing["current_price_cents"] is not None
    ]

    lowest_price_cents = (
        min(prices)
        if prices
        else None
    )

    retailer_count = len({
        listing["retailer"]
        for listing in listings
    })

    return render_template(
        "index.html",
        listings=listings,
        alerts=alerts,
        lowest_price_cents=lowest_price_cents,
        retailer_count=retailer_count,
    )

@app.route("/product/<path:listing_id>")
def product_detail(
    listing_id: str,
):
    listing = database.get_dashboard_listing(
        listing_id
    )

    if listing is None:
        abort(404)

    history = database.get_price_history(
        listing_id,
        days=30,
    )

    chart_labels: list[str] = []

    for row in history: 
        try:
            checked_at = datetime.fromisoformat(
                row["checked_at"]
            )

            chart_labels.append(
                checked_at.strftime(
                    "%b %d"
                )
            )
        except ValueError:
            chart_labels.append(
                row["checked_at"]
            )

    chart_prices = [
        row["price_cents"] / 100
        for row in history
    ]

    return render_template(
        "product.html",
        listing=listing,
        chart_labels=chart_labels,
        chart_prices=chart_prices,
    )

if __name__ == "__main__":
    app.run(
        debug=True,
        port=5000,
    )