from __future__ import annotations
import re
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup
from playwright.sync_api import (
    BrowserContext,
    Playwright,
    sync_playwright,
)
from filters import matches_product_specs
from models import Listing
from retailers.base import RetailerClient


class NeweggClient(RetailerClient):
    BASE_URL = "https://www.newegg.com"
    SEARCH_URL = "https://www.newegg.com/p/pl?d={query}"

    DEFAULT_SEARCH_TERMS = (
        "ddr5 5600 sodimm",
        "32gb ddr5 sodimm",
        "32gb laptop memory ddr5 5600",
    )

    def __init__(
        self,
        search_terms: tuple[str, ...] | None = None,
        timeout: int = 30_000,
        headless: bool = False,
    ) -> None:
        self.search_terms = (
            search_terms or self.DEFAULT_SEARCH_TERMS
        )
        self.timeout = timeout
        self.headless = headless

    def search(self) -> list[Listing]:
        listings_by_id: dict[str, Listing] = {}

        with sync_playwright() as playwright:
            context = self._create_browser_context(
                playwright
            )

            try:
                for search_term in self.search_terms:
                    search_url = self._build_search_url(
                        search_term
                    )

                    try:
                        soup = self._fetch_search_page(
                            context,
                            search_url,
                        )

                        discovered_listings = (
                            self.parse_search_page(soup)
                        )
                    except Exception as error:
                        print(
                            "Newegg search failed for "
                            f"{search_term!r}: "
                            f"{type(error).__name__}: "
                            f"{error}"
                        )
                        continue

                    for listing in discovered_listings:
                        # Only open product pages for
                        # listings matching the requested
                        # RAM specifications.
                        if not matches_product_specs(
                            listing
                        ):
                            continue

                        try:
                            completed_listing = (
                                self._enrich_listing_seller(
                                    listing,
                                    context,
                                )
                            )
                        except Exception as error:
                            print(
                                "Could not determine "
                                "Newegg seller for "
                                f"{listing.listing_id}: "
                                f"{type(error).__name__}: "
                                f"{error}"
                            )

                            completed_listing = listing

                        listings_by_id[
                            completed_listing.listing_id
                        ] = completed_listing
            finally:
                context.browser.close()

        return list(listings_by_id.values())

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

    def _fetch_search_page(
        self,
        context: BrowserContext,
        url: str,
    ) -> BeautifulSoup:
        page = context.new_page()

        try:
            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=self.timeout,
            )

            if response is None:
                raise RuntimeError(
                    "Newegg returned no response."
                )

            if response.status >= 400:
                raise RuntimeError(
                    "Newegg returned HTTP "
                    f"{response.status}."
                )

            try:
                page.wait_for_selector(
                    ".item-cell",
                    timeout=10_000,
                )
            except Exception:
                # An empty results page may legitimately
                # contain no item cards.
                pass

            return BeautifulSoup(
                page.content(),
                "html.parser",
            )
        finally:
            page.close()

    def _fetch_product_page(
        self,
        context: BrowserContext,
        url: str,
    ) -> BeautifulSoup:
        page = context.new_page()

        try:
            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=self.timeout,
            )

            if response is None:
                raise RuntimeError(
                    "Newegg product page returned "
                    "no response."
                )

            if response.status >= 400:
                raise RuntimeError(
                    "Newegg product page returned HTTP "
                    f"{response.status}."
                )

            try:
                page.wait_for_function(
                    """
                    () => document.body.innerText
                        .toLowerCase()
                        .includes("sold by")
                    """,
                    timeout=10_000,
                )
            except Exception:
                # Seller parsing will return Unknown if
                # the text never appears.
                pass

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

        for card in soup.select(".item-cell"):
            listing = self._parse_product_card(card)

            if listing is not None:
                listings.append(listing)

        return listings

    def _parse_product_card(
        self,
        card,
    ) -> Listing | None:
        title_link = card.select_one("a.item-title")
        price_element = card.select_one(
            ".price-current"
        )

        if title_link is None or price_element is None:
            return None

        name = title_link.get_text(
            " ",
            strip=True,
        )

        raw_url = title_link.get("href")

        if not name or not raw_url:
            return None

        url = urljoin(
            self.BASE_URL,
            str(raw_url),
        )

        item_number = self._extract_item_number(url)

        if item_number is None:
            return None

        price = self._parse_price(
            price_element.get_text(
                "",
                strip=True,
            )
        )

        if price is None:
            return None

        card_text = card.get_text(
            " ",
            strip=True,
        )

        seller = self._extract_seller(card)
        model_number = self._extract_model_number(
            card_text
        )
        image_url = self._extract_image_url(card)

        in_stock = not self._contains_any(
            card_text.lower(),
            (
                "out of stock",
                "sold out",
                "currently unavailable",
            ),
        )

        condition = (
            "refurbished"
            if "refurbished" in name.lower()
            else "new"
        )

        return Listing(
            listing_id=f"newegg:{item_number}",
            retailer="Newegg",
            seller=seller,
            name=name,
            price=price,
            url=url,
            in_stock=in_stock,
            checked_at=datetime.now(timezone.utc),
            model_number=model_number,
            image_url=image_url,
            condition=condition,
        )

    def _enrich_listing_seller(
        self,
        listing: Listing,
        context: BrowserContext,
    ) -> Listing:
        soup = self._fetch_product_page(
            context,
            listing.url,
        )

        seller = self.parse_product_page_seller(
            soup
        )

        return replace(
            listing,
            seller=seller,
        )

    def parse_product_page_seller(
        self,
        soup: BeautifulSoup,
    ) -> str:
        """
        Extract the actual seller from a rendered
        Newegg product page.
        """
        sold_by_pattern = re.compile(
            r"^\s*Sold\s+by\s+(.+?)\s*$",
            flags=re.IGNORECASE,
        )

        for text_node in soup.find_all(
            string=re.compile(
                r"\bSold\s+by\b",
                flags=re.IGNORECASE,
            )
        ):
            parent = text_node.parent

            if parent is None:
                continue

            text = parent.get_text(
                " ",
                strip=True,
            )

            match = sold_by_pattern.match(text)

            if match:
                return self._normalize_seller_name(
                    match.group(1)
                )

        # Fallback for pages where "Sold by" and the
        # seller name appear in adjacent elements.
        page_text = soup.get_text(
            "\n",
            strip=True,
        )

        lines = [
            line.strip()
            for line in page_text.splitlines()
            if line.strip()
        ]

        for index, line in enumerate(lines):
            match = re.fullmatch(
                r"Sold\s+by\s+(.+)",
                line,
                flags=re.IGNORECASE,
            )

            if match:
                return self._normalize_seller_name(
                    match.group(1)
                )

            if (
                re.fullmatch(
                    r"Sold\s+by",
                    line,
                    flags=re.IGNORECASE,
                )
                and index + 1 < len(lines)
            ):
                return self._normalize_seller_name(
                    lines[index + 1]
                )

        return "Unknown"

    def _extract_seller(self, card) -> str:
        """
        Search-card seller parsing is only a preliminary
        value. The product page lookup later replaces it
        for specification-matching products.
        """
        seller_element = card.select_one(
            ".item-seller"
        )

        if seller_element is not None:
            seller_text = seller_element.get_text(
                " ",
                strip=True,
            )

            match = re.search(
                r"(?:sold|shipped)\s+by\s+(.+)",
                seller_text,
                flags=re.IGNORECASE,
            )

            if match:
                return self._normalize_seller_name(
                    match.group(1)
                )

        card_text = card.get_text(
            " ",
            strip=True,
        ).lower()

        if "sold and shipped by newegg" in card_text:
            return "Newegg"

        # Shipping alone does not prove that Newegg is
        # also the seller.
        return "Unknown"

    @staticmethod
    def _normalize_seller_name(
        seller: str,
    ) -> str:
        cleaned = re.sub(
            r"\s+",
            " ",
            seller,
        ).strip()

        cleaned = re.sub(
            r"\s+(?:Seller Profile|View Seller).*$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()

        if cleaned.lower() in {
            "newegg",
            "newegg.com",
        }:
            return "Newegg"

        return cleaned or "Unknown"

    @staticmethod
    def _extract_model_number(
        card_text: str,
    ) -> str | None:
        match = re.search(
            r"(?:model|part number)\s*#?\s*:\s*"
            r"([A-Za-z0-9._-]+)",
            card_text,
            flags=re.IGNORECASE,
        )

        if not match:
            return None

        return match.group(1).strip()

    @staticmethod
    def _extract_image_url(card) -> str | None:
        image = card.select_one(
            ".item-img img"
        )

        if image is None:
            return None

        value = (
            image.get("src")
            or image.get("data-src")
            or image.get("data-original")
        )

        if not value:
            return None

        return str(value).strip() or None

    @staticmethod
    def _extract_item_number(
        url: str,
    ) -> str | None:
        match = re.search(
            r"/p/([A-Za-z0-9-]+)",
            url,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(1).upper()

        return None

    @staticmethod
    def _parse_price(
        value: object,
    ) -> Decimal | None:
        if value is None:
            return None

        match = re.search(
            r"\$?\s*([\d,]+(?:\.\d{1,2})?)",
            str(value),
        )

        if not match:
            return None

        cleaned = match.group(1).replace(",", "")

        try:
            return Decimal(cleaned).quantize(
                Decimal("0.01")
            )
        except InvalidOperation:
            return None

    @classmethod
    def _build_search_url(
        cls,
        search_term: str,
    ) -> str:
        return cls.SEARCH_URL.format(
            query=quote_plus(search_term)
        )

    @staticmethod
    def _contains_any(
        text: str,
        values: tuple[str, ...],
    ) -> bool:
        return any(
            value in text
            for value in values
        )