from decimal import Decimal
from pathlib import Path
from bs4 import BeautifulSoup
from retailers.microcenter import MicroCenterClient
from filters import matches_requirements

PRODUCT_FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "microcenter_product.html"
)

SEARCH_FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "microcenter_search.html"
)

PRODUCT_URL = (
    "https://www.microcenter.com/"
    "product/682231/"
    "crucial-32gb-ddr5-memory-kit"
)


def load_fixture(path: Path) -> BeautifulSoup:
    html = path.read_text(
        encoding="utf-8"
    )

    return BeautifulSoup(
        html,
        "html.parser",
    )


def test_parse_microcenter_listing() -> None:
    client = MicroCenterClient(
        product_urls = (),
    )
    soup = load_fixture(PRODUCT_FIXTURE_PATH)

    listing = client.parse_listing(
        soup=soup,
        url=PRODUCT_URL,
    )

    assert listing.listing_id == (
        "microcenter:682231"
    )
    assert listing.retailer == "Micro Center"
    assert listing.seller == "Micro Center"

    assert listing.name == (
        "Crucial 32GB DDR5-5600 "
        "SODIMM Memory Kit"
    )

    assert listing.price == Decimal("89.99")
    assert listing.in_stock is True

    assert listing.brand == "Crucial"
    assert listing.model_number == (
        "CT2K16G56C46S5"
    )

    assert listing.image_url == (
        "https://example.com/"
        "crucial-memory.jpg"
    )

    assert listing.condition == "new"
    assert listing.url == PRODUCT_URL

def test_parse_microcenter_search_page() -> None:
    client = MicroCenterClient(
        product_urls=(),
    )

    soup = load_fixture(
        SEARCH_FIXTURE_PATH
    )

    listings = client.parse_search_page(
        soup
    )

    assert len(listings) == 2

    pny = listings[0]

    assert pny.listing_id == (
        "microcenter:709554"
    )
    assert pny.retailer == "Micro Center"
    assert pny.seller == "Micro Center"
    assert pny.price == Decimal("79.99")
    assert pny.brand == "PNY"
    assert pny.model_number == (
        "MN8GSD43200-TB"
    )
    assert pny.in_stock is True

    lexar = listings[1]

    assert lexar.listing_id == (
        "microcenter:694991"
    )
    assert lexar.price == Decimal(
        "429.99"
    )
    assert lexar.brand == "Lexar"
    assert lexar.model_number == (
        "LD5S16G56C46STB"
    )

def test_microcenter_matching_ram_is_accepted() -> None:
    client = MicroCenterClient(
        product_urls=(),
    )

    listings = client.parse_search_page(
        load_fixture(
            SEARCH_FIXTURE_PATH
        )
    )

    assert matches_requirements(
        listings[0]
    ) is False

    assert matches_requirements(
        listings[1]
    ) is True