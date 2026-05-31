# Price Extractor Skill

## Purpose
Pull numeric price, currency and discount data out of scraped HTML.

## Triggers
Selected when the query contains any of: `price`, `cost`, `amount`, `rate`.

## Inputs
- `scraped_urls` (list): URLs produced by `url_scraper`.

## Outputs
- `extracted_data.price` (dict):
  - `value`: Current selling price.
  - `currency`: ISO 4217 code.
  - `mrp`: Maximum retail price if available.
  - `discount_pct`: Computed discount percentage.

## Behaviour
- One row per URL; missing fields are returned as `null`.
- Multiple price candidates per page are resolved by picking the most
  prominent one (largest font / closest to "Buy" button) in Phase 2.

## Phase 1 status
Stub only.
