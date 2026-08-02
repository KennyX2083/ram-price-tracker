from decimal import Decimal
from pathlib import Path
from bs4 import BeautifulSoup
from retailers.microcenter import MicroCenterClient


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "microcenter_product.html"
)

PRODUCT_URL = (
    "https://www.microcenter.com/"
    "product/682231/"
    "crucial-32gb-ddr5-memory-kit"
)


def load_fixture() -> BeautifulSoup:
    html = FIXTURE_PATH.read_text(
        encoding="utf-8"
    )

    return BeautifulSoup(
        html,
        "html.parser",
    )


def test_parse_microcenter_listing():
    client = MicroCenterClient(
        product_urls = (),
    )
    soup = load_fixture()

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