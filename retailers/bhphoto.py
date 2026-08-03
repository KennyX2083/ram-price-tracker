from __future__ import annotations
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from models import Listing
from retailers.base import RetailerClient
from playwright.sync_api import (
    BrowserContext,
    Playwright,
    sync_playwright,
)
import json

class BHPhotoClient(RetailerClient):
    BASE_URL = "https://www.bhphotovideo.com"

    MEMORY_CATEGORY_URL = (
        "https://www.bhphotovideo.com/c/products/"
        "Computer-Memory/ci/13341"
        "?filters="
        "fct_a_speed_994%3Addr5-5600mhz%3AREGULAR%2C"
        "fct_capacity_867%3A32gb-2x16gb%3AREGULAR%2C"
        "fct_memory-type_1070%3Addr5%3AREGULAR"
    )

    def __init__(
        self,
        timeout: int = 30_000,
        headless: bool = False,
    ) -> None:
        self.timeout = timeout
        self.headless = headless

    def search(self) -> list[Listing]:
        with sync_playwright() as playwright:
            context = self._create_browser_context(
                playwright
            )

            try:
                soup = self._fetch_category_page(
                    context
                )
            finally:
                context.browser.close()

        listings = self.parse_category_page(soup)

        unique_listings: dict[str, Listing] = {}

        for listing in listings:
            unique_listings[
                listing.listing_id
            ] = listing

        return list(unique_listings.values())

    def _create_browser_context(
        self,
        playwright: Playwright,
    ) -> BrowserContext:
        browser = playwright.chromium.launch(
            headless=self.headless,
        )

        return browser.new_context(
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

    def _fetch_category_page(
        self,
        context: BrowserContext,
    ) -> BeautifulSoup:
        page = context.new_page()

        try:
            response = page.goto(
                self.MEMORY_CATEGORY_URL,
                wait_until="domcontentloaded",
                timeout=self.timeout,
            )

            if response is None:
                raise RuntimeError(
                    "B&H returned no response."
                )

            if response.status >= 400:
                raise RuntimeError(
                    f"B&H returned HTTP {response.status}."
                )

            page.locator(
                "div.bh-preloaded-data[data-data]"
            ).first.wait_for(
                state="attached",
                timeout=self.timeout,
            )

            html = page.content()

            return BeautifulSoup(
                html,
                "html.parser",
            )
        finally:
            page.close()

    def parse_category_page(
        self,
        soup: BeautifulSoup,
    ) -> list[Listing]:
        preloaded_elements = soup.select(
            "div.bh-preloaded-data[data-data]"
        )

        page_data = None

        for element in preloaded_elements:
            raw_data = element.get("data-data")

            if not raw_data:
                continue

            try:
                candidate_data = json.loads(
                    str(raw_data)
                )
            except json.JSONDecodeError:
                continue

            if "ListingStore" in candidate_data:
                page_data = candidate_data
                break

        if page_data is None:
            raise ValueError(
                "Could not find B&H listing data "
                "in the preloaded JSON."
            )

        try:
            items = (
                page_data["ListingStore"]
                ["state"]
                ["response"]
                ["data"]
                ["items"]
            )
        except (
            KeyError,
            TypeError,
        ) as error:
            raise ValueError(
                "B&H listing items were not found "
                "in the preloaded data."
            ) from error

        listings: list[Listing] = []

        for item in items:
            listing = self._parse_preloaded_item(
                item
            )

            if listing is not None:
                listings.append(listing)

        return listings

    def _parse_preloaded_item(
        self,
        item: dict,
    ) -> Listing | None:
        item_key = item.get("itemKey") or {}
        core = item.get("core") or {}
        price_info = item.get("priceInfo") or {}
        stock_info = item.get("stockInfo") or {}
        condition_flags = (
            item.get("conditionFlags") or {}
        )
        main_image = item.get("mainImage") or {}
        sku_number = item_key.get("skuNo")
        name = core.get("shortDescription")
        selling_points = item.get(
            "sellingPoints"
        ) or []
        selling_point_text = " ".join(
            str(point.get("description") or "")
            for point in selling_points
            if isinstance(point, dict)
        )
        combined_name = (
            f"{name} {selling_point_text}"
        ).strip()
        item_code = core.get("itemCode")
        model_number = core.get(
            "manufacturerCatalogNumber"
        )
        details_url = core.get("detailsUrl")
        price_value = price_info.get("price")

        if sku_number is None:
            return None

        if not isinstance(name, str) or not name.strip():
            return None

        if not isinstance(
            details_url,
            str,
        ) or not details_url.strip():
            return None

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

        url = urljoin(
            self.BASE_URL,
            details_url,
        )

        image_url = self._get_preloaded_image(
            main_image
        )

        is_used = bool(
            condition_flags.get("isUsed")
            or core.get("isUsed")
        )

        is_open_box = bool(
            condition_flags.get("isOpenBox")
        )

        stock_status = str(
            stock_info.get("status") or ""
        ).upper()

        add_to_cart_button = str(
            price_info.get("addToCartButton") or ""
        ).upper()

        non_orderable_type = price_info.get(
            "nonOrderableType"
        )

        hide_price_and_cart = bool(
            price_info.get("hidePriceAndCartSection")
        )

        in_stock = (
            stock_status == "IN_STOCK"
            and add_to_cart_button == "ADD_TO_CART"
            and non_orderable_type is None
            and not hide_price_and_cart
        )
        if is_used:
            condition = "used"
        elif is_open_box:
            condition = "open_box"
        else:
            condition = "new"

        listing_id_value = (
            str(item_code).strip()
            if item_code
            else str(sku_number)
        )

        return Listing(
            listing_id=f"bh:{listing_id_value}",
            retailer="B&H",
            seller="B&H Photo Video",
            name=combined_name,
            price=price,
            url=url,
            in_stock=in_stock,
            checked_at=datetime.now(timezone.utc),
            model_number=(
                str(model_number).strip()
                if model_number
                else None
            ),
            image_url=image_url,
            condition=condition,
        )

    @staticmethod
    def _get_preloaded_image(
        main_image: dict,
    ) -> str | None:
        for image_type in (
            "listing",
            "default",
            "detail",
            "thumbnail",
        ):
            image_data = main_image.get(
                image_type
            )

            if not isinstance(
                image_data,
                dict,
            ):
                continue

            image_url = image_data.get("url")

            if image_url:
                return str(image_url).strip()

        return None

    def _find_product_container(
        self,
        product_link,
    ):
        """
        Walk upward until we find a container that appears
        to contain a complete B&H product card.
        """
        current = product_link

        for _ in range(8):
            current = current.parent

            if current is None:
                return None

            text = current.get_text(
                " ",
                strip=True,
            )

            has_item_number = bool(
                re.search(
                    r"\bBH\s*#",
                    text,
                    flags=re.IGNORECASE,
                )
            )

            has_price = "$" in text

            if has_item_number and has_price:
                return current

        return None

    def _parse_product_container(
        self,
        container,
        product_link,
        url: str,
    ) -> Listing | None:
        text = container.get_text(
            " ",
            strip=True,
        )

        name = product_link.get_text(
            " ",
            strip=True,
        )

        if not name:
            heading = container.find(
                ["h2", "h3", "h4"]
            )

            if heading is not None:
                name = heading.get_text(
                    " ",
                    strip=True,
                )

        if not name:
            return None

        bh_number = self._extract_bh_number(text)

        if bh_number is None:
            bh_number = self._extract_product_id(
                url
            )

        if bh_number is None:
            return None

        price = self._extract_price(text)

        if price is None:
            return None

        model_number = (
            self._extract_model_number(text)
        )

        image_url = self._extract_image_url(
            container
        )

        in_stock = self._is_in_stock(text)

        condition = (
            "used"
            if self._looks_used(text)
            else "new"
        )

        return Listing(
            listing_id=f"bh:{bh_number}",
            retailer="B&H",
            seller="B&H Photo Video",
            name=name,
            price=price,
            url=url,
            in_stock=in_stock,
            checked_at=datetime.now(timezone.utc),
            model_number=model_number,
            image_url=image_url,
            condition=condition,
        )

    @staticmethod
    def _extract_bh_number(
        text: str,
    ) -> str | None:
        match = re.search(
            r"\bBH\s*#\s*([A-Za-z0-9-]+)",
            text,
            flags=re.IGNORECASE,
        )

        if not match:
            return None

        return match.group(1).upper()

    @staticmethod
    def _extract_model_number(
        text: str,
    ) -> str | None:
        match = re.search(
            r"\bMFR\s*#\s*([A-Za-z0-9._/-]+)",
            text,
            flags=re.IGNORECASE,
        )

        if not match:
            return None

        return match.group(1).strip()

    @staticmethod
    def _extract_product_id(
        url: str,
    ) -> str | None:
        match = re.search(
            r"/c/product/(\d+)",
            url,
            flags=re.IGNORECASE,
        )

        if not match:
            return None

        return match.group(1)

    @staticmethod
    def _extract_price(
        text: str,
    ) -> Decimal | None:
        # Standard display, such as $419.99.
        standard_match = re.search(
            r"\$\s*([\d,]+\.\d{2})",
            text,
        )

        if standard_match:
            return BHPhotoClient._parse_decimal(
                standard_match.group(1)
            )

        # B&H sometimes renders cents separately, causing
        # extracted text such as "$419 99".
        split_cents_match = re.search(
            r"\$\s*([\d,]+)\s+(\d{2})\b",
            text,
        )

        if split_cents_match:
            value = (
                f"{split_cents_match.group(1)}."
                f"{split_cents_match.group(2)}"
            )

            return BHPhotoClient._parse_decimal(
                value
            )

        return None

    @staticmethod
    def _parse_decimal(
        value: str,
    ) -> Decimal | None:
        cleaned = value.replace(",", "")

        try:
            return Decimal(cleaned).quantize(
                Decimal("0.01")
            )
        except InvalidOperation:
            return None

    @staticmethod
    def _extract_image_url(
        container,
    ) -> str | None:
        image = container.find("img")

        if image is None:
            return None

        value = (
            image.get("src")
            or image.get("data-src")
            or image.get("data-lazy-src")
        )

        if not value:
            return None

        return urljoin(
            BHPhotoClient.BASE_URL,
            str(value),
        )

    @staticmethod
    def _is_in_stock(
        text: str,
    ) -> bool:
        normalized = text.lower()

        unavailable_phrases = (
            "discontinued",
            "no longer available",
            "temporarily out of stock",
            "back-ordered",
            "backordered",
        )

        if any(
            phrase in normalized
            for phrase in unavailable_phrases
        ):
            return False

        available_phrases = (
            "in stock",
            "add to cart",
            "limited supply",
            "special order",
        )

        return any(
            phrase in normalized
            for phrase in available_phrases
        )

    @staticmethod
    def _looks_used(
        text: str,
    ) -> bool:
        normalized = text.lower()

        # A new product card can contain a link such as
        # "Used for $201.95". Do not label the main card
        # used solely because that link exists.
        if "condition:" in normalized:
            return True

        return normalized.startswith("used ")