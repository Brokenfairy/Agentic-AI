# Location Extractor Skill

## Purpose
Pull store address / geo information out of scraped pages.

## Triggers
Selected when the query contains any of: `location`, `address`, `nearby`.

## Inputs
- `scraped_urls` (list): URLs produced by `url_scraper`.

## Outputs
- `extracted_data.location` (dict):
  - `address`, `city`, `country`: Free-form strings.
  - `lat`, `lng`: Numeric coordinates when present.

## Behaviour
- Prefers schema.org `PostalAddress` blocks; falls back to text heuristics.
- Coordinates are returned as `null` when absent.

## Phase 1 status
Stub only.
