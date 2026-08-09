from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlparse, urljoin, urlunparse
from bs4 import BeautifulSoup
from models import Listing
from retailers.manual import ManualURLClient
from playwright.sync_api import BrowserContext, sync_playwright

class MicroCenterClient(ManualURLClient):
    BASE_URL = "https://www.microcenter.com"

    LAPTOP_MEMORY_URL = (
        "https://www.microcenter.com/search/"
        "search_results.aspx"
        "?fq=category%3ALaptop+Memory%2FRAM%7C423"
    )

    NYC_STORES = {
        "115": "Brooklyn",
        "145": "Flushing",
    }   

    def __init__(
            self,
            product_urls: tuple[str, ...] | list[str] | None = None,
            store_ids: tuple[str, ...] | list[str] | None = None,
            timeout: int = 30_000,
            headless: bool = False,
    ) -> None:
        super().__init__(
            product_urls=product_urls or (),
            timeout = timeout,
            headless = headless,
        )

        self.store_ids = list(
            store_ids
            if store_ids is not None
            else self.NYC_STORES.keys()
        )

    def _build_search_url(
        self,
        store_id: str,
    ) -> str:
        return (
            f"{self.LAPTOP_MEMORY_URL}"
            f"&storeid={store_id}"
        )

    def search(self) -> list[Listing]:
        listings_by_id: dict[str, Listing] = {}

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=self.headless,
            )

            try:
                for store_id in self.store_ids:
                    store_name = self.NYC_STORES.get(
                        store_id,
                        store_id,
                    )

                    print(
                        f"Checking Micro Center store: "
                        f"{store_name}"
                    )

                    context = browser.new_context(
                        viewport={
                            "width": 1440,
                            "height": 900,
                        },
                        locale="en-US",
                        user_agent=(
                            "Mozilla/5.0 "
                            "(Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 "
                            "(KHTML, like Gecko) "
                            "Chrome/131.0.0.0 Safari/537.36"
                        ),
                    )

                    try:
                        soup = self._fetch_search_page(
                            context=context,
                            store_id=store_id,
                        )

                        listings = self.parse_search_page(
                            soup
                        )

                        for listing in listings:
                            listings_by_id[
                                listing.listing_id
                            ] = listing

                    except Exception as error:
                        print(
                            f"Could not search {store_name}: "
                            f"{type(error).__name__}: "
                            f"{error}"
                        )

                    finally:
                        context.close()

            finally:
                browser.close()

        return list(
            listings_by_id.values()
        )

    def _fetch_search_page(
        self,
        context: BrowserContext,
        store_id: str,
        ) -> BeautifulSoup:
        page = context.new_page()

        try:
            search_url = self._build_search_url(
                store_id
            )

            response = page.goto(
                search_url,
                wait_until="domcontentloaded",
                timeout=self.timeout,
            )

            if response is None:
                raise RuntimeError(
                    "Micro Center search page "
                    "returned no response."
                )

            if response.status >= 400:
                raise RuntimeError(
                    "Micro Center search page returned "
                    f"HTTP {response.status}."
                )

            try:
                page.wait_for_selector(
                    "#productGrid li.product_wrapper",
                    timeout=15_000,
                )
            except Exception:
                pass

            page.wait_for_timeout(3000)

            return BeautifulSoup(
                page.content(),
                "html.parser",
            )
        finally:
            page.close()

    def parse_search_page(
        self,
        soup: BeautifulSoup,
    ) -> list[Listing]:
        listings: list[Listing] = []

        product_cards = soup.select(
            "#productGrid li.product_wrapper"
        )

        for card in product_cards:
            listing = self._parse_search_card(
                card
            )

            if listing is not None:
                listings.append(listing)

        return listings

    def _parse_search_card(
        self,
        card,
    ) -> Listing | None:
        product_link = card.select_one(
            ".pDescription .h2 a[data-id]"
        )

        if product_link is None:
            return None

        raw_url = product_link.get("href")
        product_id = product_link.get("data-id")
        raw_price = product_link.get("data-price")

        name = (
            product_link.get("data-name")
            or product_link.get_text(
                " ",
                strip=True,
            )
        )

        brand = product_link.get("data-brand")

        if not raw_url:
            return None

        if not product_id:
            return None

        if not name:
            return None

        price = self._parse_price(
            raw_price
        )

        if price is None:
            return None

        url = urljoin(
            self.BASE_URL,
            str(raw_url),
        )

        parsed_url = urlparse(url)

        url = parsed_url._replace(
            query="",
            fragment="",
        ).geturl()

        card_text = card.get_text(
            " ",
            strip=True,
        )

        image_url = self._extract_search_image(
            card
        )

        model_number = (
            self._extract_model_from_name(
                str(name)
            )
        )

        in_stock = self._search_card_in_stock(
            card_text
        )

        condition = (
            "refurbished"
            if self._contains_any(
                str(name).lower(),
                (
                    "refurbished",
                    "certified pre-owned",
                    "pre-owned",
                ),
            )
            else "new"
        )

        return Listing(
            listing_id=(
                f"microcenter:{product_id}"
            ),
            retailer="Micro Center",
            seller="Micro Center",
            name=str(name).strip(),
            price=price,
            url=url,
            in_stock=in_stock,
            checked_at=datetime.now(timezone.utc),
            brand=(
                str(brand).strip()
                if brand
                else None
            ),
            model_number=model_number,
            image_url=image_url,
            condition=condition,
        )

    @classmethod
    def _extract_search_image(
        cls,
        card,
    ) -> str | None:
        image = card.select_one(
            ".result_left img"
        )

        if image is None:
            image = card.find("img")

        if image is None:
            return None

        raw_url = (
            image.get("src")
            or image.get("data-src")
            or image.get("data-original")
            or image.get("data-lazy-src")
        )

        if not raw_url:
            return None

        return urljoin(
            cls.BASE_URL,
            str(raw_url),
        )

    @staticmethod
    def _extract_model_from_name(
        name: str,
    ) -> str | None:
        patterns = (
            r"\bModel\s+([A-Za-z0-9._-]+)\b",
            r"\bModel:\s*([A-Za-z0-9._-]+)\b",
            r"\b(?:Module|Kit)\s+([A-Z0-9][A-Za-z0-9._-]+)$",
        )

        for pattern in patterns:
            match = re.search(
                pattern,
                name,
                flags=re.IGNORECASE,
            )

            if match:
                return match.group(1).strip()

        last_token_match = re.search(
            r"\b([A-Z0-9][A-Za-z0-9._-]{5,})$",
            name.strip(),
        )

        if last_token_match:
            candidate = last_token_match.group(1)

            if any(
                character.isdigit()
                for character in candidate
            ):
                return candidate

        return None

    @staticmethod
    def _search_card_in_stock(
        card_text: str,
    ) -> bool:
        normalized = re.sub(
            r"\s+",
            " ",
            card_text.lower(),
        ).strip()

        unavailable_phrases = (
            "out of stock",
            "sold out",
            "unavailable",
            "discontinued",
            "no longer carried",
            "0 in stock",
        )

        if any(
            phrase in normalized
            for phrase in unavailable_phrases
        ):
            return False

        available_phrases = (
            "in stock",
            "add to cart",
            "available for shipping",
            "ship this item",
            "special order",
        )

        if any(
            phrase in normalized
            for phrase in available_phrases
        ):
            return True

        # Search results only include products available
        # for the selected store/shipping context, so use
        # True when there is no explicit unavailable state.
        return True

    @staticmethod
    def _contains_any(
        text: str,
        values: tuple[str, ...],
    ) -> bool:
        return any(
            value in text
            for value in values
        )

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
        if product_id is None:
            raise ValueError(
                "Micro Center URL does not contain "
                "a numeric product ID."
            )

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
    ) -> str | None:
        path = urlparse(url).path

        match = re.search(
            r"/product/(\d+)",
            path,
        )

        if match:
            return match.group(1)

        return None

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