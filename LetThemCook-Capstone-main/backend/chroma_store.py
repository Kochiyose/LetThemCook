from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils.embedding_functions.ollama_embedding_function import (
    OllamaEmbeddingFunction,
)


class RecipeVectorStore:
    def __init__(self, base_dir: Path) -> None:
        self.collection_name = os.getenv("CHROMA_COLLECTION", "letthemcook_recipes")
        self.embedding_model = os.getenv("CHROMA_EMBED_MODEL", "all-minilm")
        self.client = chromadb.PersistentClient(path=str(base_dir / "chroma_db"))
        self.embedding_function = OllamaEmbeddingFunction(
            url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model_name=self.embedding_model,
        )
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function,
        )

    @staticmethod
    def recipe_document(recipe: dict[str, Any]) -> str:
        return "\n".join(
            [
                f"Recipe name: {recipe.get('name', '')}",
                f"Meal type: {recipe.get('mealType', '')}",
                f"Category: {recipe.get('sourceCategory', '')}",
                f"Keywords: {', '.join(recipe.get('keywords', []))}",
                f"Ingredients: {', '.join(recipe.get('allIngredients', []))}",
                f"Instructions: {' '.join(recipe.get('instructions', [])[:6])}",
            ]
        )

    def count(self) -> int:
        return self.collection.count()

    def rebuild(self, recipes: list[dict[str, Any]], batch_size: int = 50) -> int:
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function,
        )

        for start in range(0, len(recipes), batch_size):
            batch = recipes[start : start + batch_size]
            self.collection.upsert(
                ids=[str(recipe["id"]) for recipe in batch],
                documents=[self.recipe_document(recipe) for recipe in batch],
                metadatas=[
                    {
                        "recipe_id": int(recipe["id"]),
                        "name": str(recipe.get("name", "")),
                        "mealType": str(recipe.get("mealType", "Dinner")),
                        "timeMinutes": int(recipe.get("timeMinutes", 999)),
                    }
                    for recipe in batch
                ],
            )

        return self.collection.count()

    def search_ids(
        self,
        pantry: list[str],
        meal_filter: str = "All",
        name_query: str = "",
        max_time_minutes: int | None = None,
        limit: int = 100,
    ) -> list[int]:
        if self.count() == 0:
            return []

        query_parts = ["Find the most suitable recipe"]
        if pantry:
            query_parts.append("using these available ingredients: " + ", ".join(pantry))
        if name_query.strip():
            query_parts.append("with a name or meaning similar to: " + name_query.strip())
        if meal_filter != "All":
            query_parts.append("for " + meal_filter.lower())

        filters: list[dict[str, Any]] = []
        if meal_filter != "All":
            filters.append({"mealType": {"$eq": meal_filter}})
        if max_time_minutes is not None:
            filters.append({"timeMinutes": {"$lte": int(max_time_minutes)}})

        where: dict[str, Any] | None = None
        if len(filters) == 1:
            where = filters[0]
        elif len(filters) > 1:
            where = {"$and": filters}

        query_args: dict[str, Any] = {
            "query_texts": [". ".join(query_parts)],
            "n_results": min(limit, self.count()),
            "include": ["distances"],
        }
        if where is not None:
            query_args["where"] = where

        result = self.collection.query(**query_args)
        return [int(recipe_id) for recipe_id in result.get("ids", [[]])[0]]
