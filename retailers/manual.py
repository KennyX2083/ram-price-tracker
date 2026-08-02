from __future__ import annotations
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from playwright.sync_api import (
    BrowserContext,
    Playwright,
    sync_playwright,
)
from models import Listing
from retailers.base import RetailerClient


class ManualURLClient(RetailerClient, ABC):
    def __init__(
        self,
        product_urls: tuple[str, ...] | list[str],
        timeout: int = 30_000,
        headless: bool = False,
    ) -> None:
        self.product_urls = list(product_urls)
        self.timeout = timeout
        self.headless = headless

    def search(self) -> list[Listing]:
        listings: list[Listing] = []

        with sync_playwright() as playwright:
            context = self._create_browser_context(
                playwright
            )

            try:
                for url in self.product_urls:
                    try:
                        listing = self.fetch_listing(
                            url,
                            context,
                        )
                    except Exception as error:
                        print(
                            f"Could not process {url}: "
                            f"{type(error).__name__}: {error}"
                        )
                        continue

                    if listing is not None:
                        listings.append(listing)
            finally:
                context.browser.close()

        return listings

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

    def fetch_html(
        self,
        url: str,
        context: BrowserContext,
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
                    "The browser did not receive a response."
                )

            if response.status >= 400:
                raise RuntimeError(
                    f"Page returned HTTP {response.status}."
                )

            page.wait_for_timeout(3000)

            html = page.content()

            return BeautifulSoup(
                html,
                "html.parser",
            )
        finally:
            page.close()

    @abstractmethod
    def fetch_listing(
        self,
        url: str,
        context: BrowserContext,
    ) -> Listing | None:
        raise NotImplementedError