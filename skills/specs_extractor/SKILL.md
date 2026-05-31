# Specs Extractor Skill

## Purpose
Capture technical specifications listed on the product page.

## Triggers
Selected when the query contains any of: `RAM`, `processor`, `specs`,
`storage` (case-insensitive).

## Inputs
- `scraped_urls` (list): URLs produced by `url_scraper`.

## Outputs
- `extracted_data.specs` (dict): Normalized keys such as `ram`,
  `processor`, `storage`, `display`, `battery`. Values keep their units.

## Behaviour
- Spec tables, definition lists and bullet lists are all parsed.
- Unknown keys are preserved under an `extras` dict in Phase 2.

## Phase 1 status
Stub only.
