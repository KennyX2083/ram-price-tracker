# RAM Deal Tracker

A Python application that monitors laptop DDR5 memory kits across multiple retailers and sends Discord alerts when meaningful deals appear.

The tracker maintains historical price data in SQLite, detects significant price drops, and only alerts when a product first crosses a configured threshold to prevent notification spam.

---

## Current Features

### Retailer Support

| Retailer | Status |
|----------|--------|
| Micro Center | ✅ Live |
| Newegg | ✅ Live |
| B&H Photo | ✅ Live |
| Amazon | 🚧 Planned |
| Best Buy | 🚧 Planned (API currently unavailable) |

---

## Deal Detection

The tracker currently monitors:

- DDR5
- SO-DIMM (Laptop RAM)
- 32GB kits (2×16GB)
- 5600 MT/s

Products are automatically filtered so desktop DIMMs, incorrect capacities, used products, and third-party marketplace sellers are ignored.

---

## Alert Rules

A Discord notification is sent when a product:

- crosses below a configured absolute price threshold
- crosses below a configurable percentage of its 30-day average price
- is currently in stock
- has not already generated an alert within the previous 24 hours

---

## Price History

The application stores every observation in SQLite.

Historical data is used to calculate:

- 30-day moving average
- historical price trend
- threshold crossing events
- duplicate alert prevention

---

## Discord Notifications

Alerts include:

- Product name
- Current price
- Retailer
- Seller
- Product image
- Link to product
- Alert reason
- Historical comparison (when available)

---

## Product Matching

Instead of relying only on product titles, the application enriches each listing by extracting information such as:

- Memory type
- Capacity
- Module count
- Module size
- Form factor
- Speed

This allows products from different retailers to be matched consistently even when their naming conventions differ.

---

## Testing

The project includes automated tests covering:

- Product matching
- Retailer parsers
- Database operations
- Alert generation
- Deal processor logic

Tests are written using **pytest**.

---

## Tech Stack

- Python
- SQLite
- Playwright
- BeautifulSoup4
- Requests
- Discord Webhooks
- pytest

---

## Roadmap

### ✅ Completed

- SQLite price database
- Discord webhook alerts
- Product matching engine
- Micro Center integration
- Newegg integration
- B&H integration
- Automated testing

### 🚧 In Progress

- Amazon integration

### 📋 Planned

- Windows Task Scheduler automation
- Web dashboard
- Price history charts
- Additional retailers
- Historical analytics

---

## Running

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

**Windows**

```cmd
.venv\Scripts\activate
```

Install dependencies:

```cmd
pip install -r requirements.txt
```

Create a `.env` file using `.env.example`.

Run the tracker:

```cmd
python main.py
```

Run all tests:

```cmd
pytest
```

---

## License

MIT