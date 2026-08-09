from __future__ import annotations
from typing import Any
from models import Listing
from retailers.base import RetailerClient
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

class AmazonClient(RetailerClient):
    DEFAULT_SEARCH_TERMS = (
        "32GB 2x16GB DDR5 5600 SODIMM",
        "DDR5 5600 laptop memory 32GB kit",
        "PC5-44800 2x16GB SODIMM",
    )

    def __init__(
        self,
        credential_id: str,
        credential_secret: str,
        partner_tag: str,
        marketplace: str = "www.amazon.com",
        search_terms: tuple[str, ...] | None = None,
    ) -> None:
        self.credential_id = credential_id
        self.credential_secret = credential_secret
        self.partner_tag = partner_tag
        self.marketplace = marketplace

        self.search_terms = (
            search_terms
            if search_terms is not None
            else self.DEFAULT_SEARCH_TERMS
        )

    @property
    def is_configured(self) -> bool:
        return all((
            self.credential_id,
            self.credential_secret,
            self.partner_tag,
            self.marketplace,
        ))

    def search(self) -> list[Listing]:
        if not self.is_configured:
            print(
                "Amazon skipped: "
                "API credentials are not configured."
            )
            return []

        raise NotImplementedError(
            "Live Amazon API requests "
            "are not connected yet."
        )

    def parse_search_response(
        self,
        response_data: dict[str, Any],
    ) -> list[Listing]:
        search_result = response_data.get(
            "SearchResult",
            {}
        )

        items = search_result.get(
            "Items",
            []
        )

        if not isinstance(items, list):
            return []

        listings: list[Listing] = []

        for item in items:
            if not isinstance(item, dict):
                continue

            listing = self._parse_item(item)

            if listing is not None:
                listings.append(listing)

        return listings

    def _parse_item(
        self,
        item: dict[str, Any],
    ) -> Listing | None:
        asin = item.get("ASIN")
        url = item.get("DetailPageURL")

        if not asin or not url:
            return None

        item_info = item.get(
            "ItemInfo",
            {}
        )

        title = (
            item_info
            .get("Title", {})
            .get("DisplayValue")
        )

        if not title:
            return None

        brand = (
            item_info
            .get("ByLineInfo", {})
            .get("Brand", {})
            .get("DisplayValue")
        )

        model_number = (
            item_info
            .get("ManufactureInfo", {})
            .get("ItemPartNumber", {})
            .get("DisplayValue")
        )

        offers = (
            item
            .get("Offers", {})
            .get("Listings", [])
        )

        if not offers:
            return None

        offer = offers[0]

        if not isinstance(offer, dict):
            return None

        price_value = (
            offer
            .get("Price", {})
            .get("Amount")
        )

        if price_value is None:
            return None

        try:
            price = Decimal(
                str(price_value)
            ).quantize(
                Decimal("0.01")
            )
        except InvalidOperation:
            return None

        seller = (
            offer
            .get("MerchantInfo", {})
            .get("Name")
            or "Amazon"
        )

        availability_message = str(
            offer
            .get("Availability", {})
            .get("Message")
            or ""
        ).lower()

        unavailable_phrases = (
            "out of stock",
            "unavailable",
            "currently unavailable",
        )

        in_stock = not any(
            phrase in availability_message
            for phrase in unavailable_phrases
        )

        condition_value = str(
            offer
            .get("Condition", {})
            .get("Value")
            or "New"
        ).lower()

        condition = (
            "new"
            if condition_value == "new"
            else condition_value
        )

        image_url = (
            item
            .get("Images", {})
            .get("Primary", {})
            .get("Medium", {})
            .get("URL")
        )

        return Listing(
            listing_id=f"amazon:{asin}",
            retailer="Amazon",
            seller=str(seller),
            name=str(title).strip(),
            price=price,
            url=str(url),
            in_stock=in_stock,
            checked_at=datetime.now(timezone.utc),
            brand=(
                str(brand).strip()
                if brand
                else None
            ),
            model_number=(
                str(model_number).strip()
                if model_number
                else None
            ),
            image_url=(
                str(image_url).strip()
                if image_url
                else None
            ),
            condition=condition,
        )