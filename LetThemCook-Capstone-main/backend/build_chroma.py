from update_database import validate_database


def main() -> int:
    row_count, errors, warnings = validate_database()
    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print("ChromaDB rebuild stopped because CSV validation failed.")
        return 1

    # Import Main only after the CSV passes validation.
    from Main import RECIPES, VECTOR_STORE

    total = VECTOR_STORE.rebuild(RECIPES)
    print(f"ChromaDB indexed {total} recipes.")
    if total != row_count:
        print(f"ERROR: ChromaDB has {total} records but the CSV has {row_count} rows.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
