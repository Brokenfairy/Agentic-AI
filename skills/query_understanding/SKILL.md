# Query Understanding Skill

## Purpose
Convert a natural-language user query into a structured representation
that downstream skills can consume.

## Inputs
- `original_query` (str): Raw text typed by the user.

## Outputs
- `parsed_query` (dict):
  - `entity`: The main subject of the query (e.g., "laptop", "phone").
  - `attributes`: A list of attributes of interest (e.g., `["price", "ram"]`).
  - `filters`: A dict of constraints (e.g., `{"max_price": 80000}`).

## Behaviour
- Always runs first.
- Never short-circuits the workflow; if parsing fails, returns the raw
  query as `entity` with an empty attribute list and emits a warning.

## Phase 1 status
Stub only. The real NLU pipeline (LLM-based) will be wired in Phase 2.
