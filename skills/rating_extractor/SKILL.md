# Rating Extractor Skill

## Purpose
Capture user ratings and review volume from scraped product pages.

## Triggers
Selected when the query contains any of: `rating`, `review`.

## Inputs
- `scraped_urls` (list): URLs produced by `url_scraper`.

## Outputs
- `extracted_data.rating` (dict): `value` and `scale` (typically 5 or 10).
- `extracted_data.review_count` (int): Total number of reviews.

## Behaviour
- Returns `null` for ratings on pages with no review widget.
- Both star and numeric widgets are supported in Phase 2.

## Phase 1 status
Stub only.
