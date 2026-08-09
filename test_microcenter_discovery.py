from filters import matches_requirements
from product_matching import enrich_listing
from retailers.microcenter import MicroCenterClient


def main() -> None:
    client = MicroCenterClient(
        headless=False,
    )

    listings = client.search()

    print(
        f"\nMicro Center discovered "
        f"{len(listings)} listing(s)."
    )

    qualifying_count = 0

    for listing in listings:
        enriched = enrich_listing(
            listing
        )

        matches = matches_requirements(
            enriched
        )

        print()
        print(f"Name: {listing.name}")
        print(f"Price: ${listing.price:.2f}")
        print(f"In stock: {listing.in_stock}")
        print(f"Model: {listing.model_number}")
        print(f"Matches: {matches}")
        print(f"URL: {listing.url}")

        if matches:
            qualifying_count += 1

    print(
        f"\nQualifying listings: "
        f"{qualifying_count}"
    )


if __name__ == "__main__":
    main()