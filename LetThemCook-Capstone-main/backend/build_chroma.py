from Main import RECIPES, VECTOR_STORE


if __name__ == "__main__":
    total = VECTOR_STORE.rebuild(RECIPES)
    print(f"ChromaDB indexed {total} recipes.")
