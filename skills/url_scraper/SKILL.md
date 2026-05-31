# URL Scraper Skill

## Purpose
Find candidate web pages that may contain the attributes requested in
the parsed query.

## Inputs
- `parsed_query` (dict): Output from `query_understanding`.

## Outputs
- `scraped_urls` (list[dict]): Each item has `url`, `source`, `score`.

## Behaviour
- Always runs after `query_understanding`.
- Phase 2 will use Playwright/Requests + a search API.
- In Phase 1 this is a stub and produces an empty list.

## Failure modes
- Network errors are logged but never raise; an empty `scraped_urls`
  list propagates downstream so extractors no-op gracefully.

## Phase 1 status
Stub only.
