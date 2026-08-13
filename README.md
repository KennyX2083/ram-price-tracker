# RAM Deal Tracker

A Python application that automatically monitors laptop DDR5 memory prices across multiple retailers and sends Discord alerts when meaningful deals appear.

The tracker discovers products from retailer listings, filters them against configurable hardware requirements, maintains historical pricing data in SQLite, and detects significant price drops while preventing duplicate notifications.

---

## Current Features

### Retailer Support

| Retailer     | Status                                                |
| ------------ | ----------------------------------------------------- |
| Micro Center | ✅ Live — automatic Brooklyn & Flushing discovery      |
| Newegg       | ✅ Live — automatic product discovery                  |
| B&H Photo    | ✅ Live — automatic product discovery                  |
| Amazon       | 🚧 Parser implemented — live API requires credentials |
| Best Buy     | ⏸️ API integration postponed                          |

The tracker automatically discovers products from supported retailers rather than requiring individual product URLs.

Micro Center currently monitors inventory from the **Brooklyn and Flushing, NY** locations.

---

## Deal Detection

The tracker currently targets:

* DDR5
* SO-DIMM / laptop memory
* 32GB total capacity
* 2×16GB kits
* 5600 MT/s

Listings are automatically parsed and filtered before entering the price-tracking pipeline.

Products that do not meet the configured requirements are ignored.

## Automatic Product Discovery

Supported retailers are searched automatically for relevant laptop memory products.

The discovery pipeline:

1. Searches retailer product/category pages
2. Extracts available product listings
3. Normalizes retailer-specific product information
4. Enriches listings with hardware specifications
5. Filters listings against the configured RAM requirements
6. Records qualifying products and prices in SQLite
7. Evaluates each product against the configured alert rules

This allows the tracker to discover newly listed products without manually adding individual product URLs.

---

## Alert Rules

A Discord notification can be triggered when a qualifying product:

* falls below a configured absolute price threshold
* falls a configured percentage below its 30-day average
* is currently in stock
* is sold by an approved retailer or seller
* has not already generated a duplicate alert within the configured cooldown period

The default duplicate alert cooldown is **24 hours**.

Alert state is tracked so repeated checks do not continuously notify for the same deal.

---

## Price History

Every qualifying product observation is stored in SQLite.

Historical data is used for:

* 30-day moving averages
* Price history tracking
* Threshold crossing detection
* Duplicate alert prevention
* Historical deal evaluation

The database maintains separate records for:

* Product listings
* Price observations
* Alert history

This allows the tracker to build a pricing history automatically as scheduled checks run.

---

## Discord Notifications

Deal alerts can include:

* Product name
* Current price
* Retailer
* Seller
* Product image
* Product link
* Alert reason
* 30-day average
* Percentage below historical average

Notifications are delivered using Discord webhooks.

---


## Automated Execution

The tracker is configured to run automatically using **Windows Task Scheduler**.

A `run_tracker.bat` script:

1. Changes to the project directory
2. Activates the project's Python virtual environment
3. Runs `main.py`
4. Records console output and errors
5. Deactivates the virtual environment

Scheduled runs allow the price database to accumulate observations without requiring the tracker to be started manually.

### Logging

Automated runs are written to:

```text
data/tracker.log
```

The log records:

* Run start and finish times
* Retailer discovery results
* Filtered products
* Qualifying products
* Current prices
* Alert decisions
* Runtime errors

Database and log files are excluded from Git.

---

## Amazon Support

There is implementation for the Amazon section of the program but due to not having official API credentials at this time live support will be added later.

---

## Tech Stack

* Python
* SQLite
* Playwright
* BeautifulSoup4
* Requests
* Discord Webhooks
* pytest
* Windows Task Scheduler

---

## Roadmap

### ✅ Completed

* SQLite price database
* Historical price observations
* 30-day moving average calculations
* Discord webhook alerts
* Duplicate alert prevention
* Product specification enrichment
* Product matching and filtering
* Micro Center automatic discovery
  * Brooklyn, NY
  * Flushing, NY
* Newegg automatic discovery
* B&H Photo automatic discovery
* Amazon response parser
* Automated pytest coverage
* Windows Task Scheduler automation
* Scheduled logging

### 🚧 In Progress

* Web dashboard

### 📋 Future Improvements (Hopefully)

* Live Amazon API integration
* Best Buy integration
* Additional retailers
* Additional Micro Center locations
* Improved retailer-specific metadata extraction
* Expanded historical analytics

---

## Automated Runs

On Windows, `run_tracker.bat` can be executed manually with:

```cmd
run_tracker.bat
```

The project can also be configured in Windows Task Scheduler to execute this script periodically.

Scheduled output is written to:

```text
data/tracker.log
```

---

## Current Project Status

The core tracking pipeline is working.

Micro Center, Newegg, and B&H Photo are currently supported as live retailer sources.

Looking to add a web dashboard as a final main goal to the project. 

---