"""Validate the LetThemCook CSV before rebuilding ChromaDB.

Run this file before ``build_chroma.py``. It intentionally does not rename or
silently rewrite the database; confirmed data corrections remain reviewable in
version control.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "data" / "LetThemCook_Cleaned.csv"
REQUIRED_COLUMNS = [
    "Name",
    "RecipeCategory",
    "Keywords",
    "RecipeIngredientParts",
    "RecipeInstructions",
    "Calories",
    "TotalTime_Mins",
]


def validate_database(path: Path = DATABASE_PATH) -> tuple[int, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not path.exists():
        return 0, [f"Database file does not exist: {path}"], warnings

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        if headers != REQUIRED_COLUMNS:
            errors.append(
                "CSV columns do not match the required schema. "
                f"Expected {REQUIRED_COLUMNS}; received {headers}."
            )
        rows = list(reader)

    names: dict[str, list[int]] = defaultdict(list)
    for row_number, row in enumerate(rows, start=2):
        for column in REQUIRED_COLUMNS:
            if not str(row.get(column, "")).strip():
                errors.append(f"Row {row_number} has an empty {column} value.")

        name = str(row.get("Name", "")).strip()
        if name:
            names[name.casefold()].append(row_number)

        for column in ["Calories", "TotalTime_Mins"]:
            raw_value = str(row.get(column, "")).strip()
            try:
                value = float(raw_value)
                if not math.isfinite(value) or value < 0:
                    raise ValueError
                if column == "TotalTime_Mins" and value == 0:
                    raise ValueError
            except ValueError:
                errors.append(
                    f"Row {row_number} has an invalid {column} value: {raw_value!r}."
                )

        try:
            if float(row.get("TotalTime_Mins", 0)) > 1440:
                warnings.append(
                    f"Row {row_number} ({name}) exceeds 24 hours; verify that marinating time is intended."
                )
        except (TypeError, ValueError):
            pass

    for normalized_name, row_numbers in names.items():
        if len(row_numbers) > 1:
            errors.append(
                f"Duplicate recipe name {normalized_name!r} appears on CSV rows {row_numbers}."
            )

    return len(rows), errors, warnings


def main() -> int:
    row_count, errors, warnings = validate_database()
    print(f"Validated {row_count} recipe rows in {DATABASE_PATH.name}.")
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")

    if errors:
        print(f"Validation failed with {len(errors)} error(s).")
        return 1

    print("CSV database validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
