from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from models import Listing
from retailers.manual import ManualURLClient

from playwright.sync_api import BrowserContext


class MicroCenterClient(ManualURLClient):
    def fetch_listing(
        self,
        url: str,
        context: BrowserContext,
    ) -> Listing | None:
        soup = self.fetch_html(
            url,
            context,
        )

        return self.parse_listing(
            soup=soup,
            url=url,
        )


    def parse_listing(
        self,
        soup: BeautifulSoup,
        url: str,
    ) -> Listing:
        product_data = self._find_product_json_ld(
            soup
        )

        name = self._get_name(
            soup=soup,
            product_data=product_data,
        )

        price = self._get_price(
            soup=soup,
            product_data=product_data,
        )

        if not name:
            raise ValueError(
                "Could not find the product name."
            )

        if price is None:
            raise ValueError(
                "Could not find the product price."
            )

        product_id = self._extract_product_id(url)

        availability = self._get_availability(
            soup=soup,
            product_data=product_data,
        )

        image_url = self._get_image_url(
            soup=soup,
            product_data=product_data,
        )

        brand = self._get_brand(product_data)

        model_number = self._optional_string(
            product_data.get("model")
            or product_data.get("mpn")
            or product_data.get("sku")
        )

        return Listing(
            listing_id=f"microcenter:{product_id}",
            retailer="Micro Center",
            seller="Micro Center",
            name=name,
            price=price,
            url=url,
            in_stock=availability,
            checked_at=datetime.now(timezone.utc),
            brand=brand,
            model_number=model_number,
            image_url=image_url,
            condition="new",
        )

    def _find_product_json_ld(
        self,
        soup: BeautifulSoup,
    ) -> dict[str, Any]:
        scripts = soup.find_all(
            "script",
            attrs={"type": "application/ld+json"},
        )

        for script in scripts:
            raw_json = script.string

            if not raw_json:
                continue

            try:
                data = json.loads(raw_json)
            except json.JSONDecodeError:
                continue

            product = self._find_product_object(data)

            if product is not None:
                return product

        return {}

    def _find_product_object(
        self,
        value: Any,
    ) -> dict[str, Any] | None:
        if isinstance(value, dict):
            object_type = value.get("@type")

            if object_type == "Product":
                return value

            if (
                isinstance(object_type, list)
                and "Product" in object_type
            ):
                return value

            graph = value.get("@graph")

            if graph is not None:
                product = self._find_product_object(
                    graph
                )

                if product is not None:
                    return product

            for nested_value in value.values():
                product = self._find_product_object(
                    nested_value
                )

                if product is not None:
                    return product

        if isinstance(value, list):
            for item in value:
                product = self._find_product_object(
                    item
                )

                if product is not None:
                    return product

        return None

    def _get_name(
        self,
        soup: BeautifulSoup,
        product_data: dict[str, Any],
    ) -> str | None:
        json_name = self._optional_string(
            product_data.get("name")
        )

        if json_name:
            return json_name

        meta_name = soup.select_one(
            'meta[property="og:title"]'
        )

        if meta_name:
            content = meta_name.get("content")

            if content:
                return str(content).strip()

        heading = soup.find("h1")

        if heading:
            return heading.get_text(
                " ",
                strip=True,
            )

        return None

    def _get_price(
        self,
        soup: BeautifulSoup,
        product_data: dict[str, Any],
    ) -> Decimal | None:
        offer = self._get_offer(product_data)

        price = self._parse_price(
            offer.get("price")
        )

        if price is not None:
            return price

        meta_price = soup.select_one(
            'meta[property="product:price:amount"]'
        )

        if meta_price:
            price = self._parse_price(
                meta_price.get("content")
            )

            if price is not None:
                return price

        item_price = soup.select_one(
            '[itemprop="price"]'
        )

        if item_price:
            price = self._parse_price(
                item_price.get("content")
                or item_price.get_text(
                    " ",
                    strip=True,
                )
            )

            if price is not None:
                return price

        return None

    def _get_availability(
        self,
        soup: BeautifulSoup,
        product_data: dict[str, Any],
    ) -> bool:
        offer = self._get_offer(product_data)

        availability = str(
            offer.get("availability") or ""
        ).lower()

        if any(
            state in availability
            for state in (
                "instock",
                "limitedavailability",
                "onlineonly",
                "preorder",
            )
        ):
            return True

        if any(
            state in availability
            for state in (
                "outofstock",
                "soldout",
                "discontinued",
            )
        ):
            return False

        page_text = soup.get_text(
            " ",
            strip=True,
        ).lower()

        if any(
            phrase in page_text
            for phrase in (
                "no longer carried",
                "out of stock",
                "sold out",
                "0 new in stock",
            )
        ):
            return False

        if any(
            phrase in page_text
            for phrase in (
                "add to cart",
                "new in stock",
                "available for shipping",
            )
        ):
            return True

        return False

    def _get_image_url(
        self,
        soup: BeautifulSoup,
        product_data: dict[str, Any],
    ) -> str | None:
        image = product_data.get("image")

        if isinstance(image, str):
            return image.strip() or None

        if isinstance(image, list) and image:
            first_image = image[0]

            if isinstance(first_image, str):
                return first_image.strip() or None

        if isinstance(image, dict):
            image_url = self._optional_string(
                image.get("url")
                or image.get("contentUrl")
            )

            if image_url:
                return image_url

        meta_image = soup.select_one(
            'meta[property="og:image"]'
        )

        if meta_image:
            return self._optional_string(
                meta_image.get("content")
            )

        return None

    def _get_brand(
        self,
        product_data: dict[str, Any],
    ) -> str | None:
        brand = product_data.get("brand")

        if isinstance(brand, str):
            return brand.strip() or None

        if isinstance(brand, dict):
            return self._optional_string(
                brand.get("name")
            )

        return None

    def _get_offer(
        self,
        product_data: dict[str, Any],
    ) -> dict[str, Any]:
        offers = product_data.get("offers")

        if isinstance(offers, dict):
            return offers

        if isinstance(offers, list):
            for offer in offers:
                if isinstance(offer, dict):
                    return offer

        return {}

    @staticmethod
    def _extract_product_id(
        url: str,
    ) -> str:
        path = urlparse(url).path

        match = re.search(
            r"/product/(\d+)",
            path,
        )

        if match:
            return match.group(1)

        raise ValueError(
            "Micro Center URL does not contain "
            "a numeric product ID."
        )

    @staticmethod
    def _parse_price(
        value: object,
    ) -> Decimal | None:
        if value is None:
            return None

        cleaned = re.sub(
            r"[^0-9.]",
            "",
            str(value),
        )

        if not cleaned:
            return None

        try:
            return Decimal(cleaned).quantize(
                Decimal("0.01")
            )
        except InvalidOperation:
            return None

    @staticmethod
    def _optional_string(
        value: object,
    ) -> str | None:
        if value is None:
            return None

        text = str(value).strip()

        return text or None