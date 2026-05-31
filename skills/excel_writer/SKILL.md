# Excel Writer Skill

## Purpose
Serialize the workflow's `extracted_data` into a `.xlsx` file that the
user can download.

## Inputs
- `extracted_data` (dict): Populated by extractor skills.

## Outputs
- `excel_path` (str): Absolute path of the written file inside
  `outputs/`.

## Behaviour
- Always runs as the final skill.
- Each top-level key in `extracted_data` becomes its own sheet
  (e.g., `price`, `rating`, `specs`).
- Uses `pandas` + `openpyxl` under the hood.

## Current Status
Active export stage. Phase 5 now writes Excel plus companion CSV, JSON, and Markdown artifacts through the export system.
