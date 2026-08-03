from decimal import Decimal
from pathlib import Path

from bs4 import BeautifulSoup

from filters import matches_requirements
from retailers.bhphoto import BHPhotoClient


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "bh_search.html"
)


def load_fixture() -> BeautifulSoup:
    html = FIXTURE_PATH.read_text(
        encoding="utf-8"
    )

    return BeautifulSoup(
        html,
        "html.parser",
    )


def test_parse_bh_category_page() -> None:
    client = BHPhotoClient()

    listings = client.parse_category_page(
        load_fixture()
    )

    assert len(listings) == 3

    crucial = listings[0]

    assert crucial.listing_id == (
        "bh:CR2K16G56C4L"
    )

    assert crucial.retailer == "B&H"

    assert crucial.seller == (
        "B&H Photo Video"
    )

    assert crucial.price == Decimal(
        "419.99"
    )

    assert crucial.model_number == (
        "CT2K16G56C46S5"
    )

    assert crucial.image_url == (
        "https://example.com/crucial.jpg"
    )

    assert crucial.in_stock is True
    assert crucial.condition == "new"


def test_valid_bh_ram_matches_filter() -> None:
    client = BHPhotoClient()

    listings = client.parse_category_page(
        load_fixture()
    )

    assert matches_requirements(
        listings[0]
    ) is True


def test_bh_desktop_memory_is_rejected() -> None:
    client = BHPhotoClient()

    listings = client.parse_category_page(
        load_fixture()
    )

    desktop_listing = listings[1]

    assert desktop_listing.price == Decimal(
        "399.99"
    )

    assert matches_requirements(
        desktop_listing
    ) is False


def test_bh_wrong_capacity_is_rejected() -> None:
    client = BHPhotoClient()

    listings = client.parse_category_page(
        load_fixture()
    )

    wrong_capacity_listing = listings[2]

    assert matches_requirements(
        wrong_capacity_listing
    ) is False