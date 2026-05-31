# Availability Extractor Skill

## Purpose
Detect whether each scraped page advertises the item as available.

## Triggers
Selected when the query contains any of: `availability`, `stock`.

## Inputs
- `scraped_urls` (list): URLs produced by `url_scraper`.

## Outputs
- `extracted_data.availability` (dict):
  - `status`: One of `in_stock`, `out_of_stock`, `preorder`, `unknown`.
  - `eta_days`: Estimated delivery in days when shown by the site.

## Behaviour
- Defaults to `unknown` when no clear signal is present.
- Reads structured data (`<meta>`, JSON-LD) before falling back to text.

## Phase 1 status
Stub only.
