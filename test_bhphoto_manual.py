from filters import matches_requirements
from product_matching import enrich_listing
from retailers.bhphoto import BHPhotoClient


def main() -> None:
    client = BHPhotoClient(
        headless=False,
    )

    listings = client.search()

    print(
        f"\nB&H discovered "
        f"{len(listings)} unique listing(s)."
    )

    matching_count = 0

    for listing in listings:
        enriched = enrich_listing(listing)
        matches = matches_requirements(enriched)

        print()
        print(f"Name: {listing.name}")
        print(f"Price: ${listing.price:.2f}")
        print(f"Seller: {listing.seller}")
        print(f"Model: {listing.model_number}")
        print(f"In stock: {listing.in_stock}")
        print(f"Matches: {matches}")
        print(f"URL: {listing.url}")

        if matches:
            matching_count += 1

    print(
        f"\nQualifying listings: "
        f"{matching_count}"
    )


if __name__ == "__main__":
    main()