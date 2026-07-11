"""LetThemCook FastAPI backend.

The app uses a bundled CSV file as a mock recipe database and exposes it to the
React/Vite UI through REST endpoints. Ollama is optional; if it is not running,
the backend still replies using database search results.
"""

from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path
from typing import Any, Literal

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from chroma_store import RecipeVectorStore

BASE_DIR = Path(__file__).resolve().parent
RECIPES_PATH = BASE_DIR / "data" / "LetThemCook_Cleaned.csv"
ENV_PATH = BASE_DIR / ".env"


def load_local_env() -> None:
    """Load simple KEY=value pairs from backend/.env without requiring python-dotenv."""
    if not ENV_PATH.exists():
        return

    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # Real environment variables still win over .env values.
        os.environ.setdefault(key, value)


load_local_env()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
USE_OLLAMA = os.getenv("USE_OLLAMA", "false").lower() in {"1", "true", "yes", "y"}
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "8"))

app = FastAPI(title="LetThemCook Backend API", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RecipeSearchRequest(BaseModel):
    pantry: list[str] = Field(default_factory=list)
    mealFilter: Literal["All", "Breakfast", "Lunch", "Dinner"] = "All"
    nameQuery: str = ""


class ChatRequest(BaseModel):
    user_message: str


class RecipeQuery(BaseModel):
    user_ingredients: str
    max_time_minutes: int = 60


def normalize(text: Any) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", str(text).lower()).strip()


def parse_r_vector(value: Any) -> list[str]:
    """Parse Food.com style R vectors: c("item one", "item two")."""
    if value is None:
        return []

    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return []

    # Most records are c("a", "b"). This keeps commas inside quoted strings.
    quoted = re.findall(r'"((?:[^"\\]|\\.)*)"', text, flags=re.DOTALL)
    if quoted:
        return [re.sub(r"\s+", " ", item.replace('\\"', '"')).strip() for item in quoted if item.strip()]

    # Fallback for plain comma-separated fields.
    text = re.sub(r"^c\(|\)$", "", text)
    return [item.strip().strip('"\'') for item in text.split(",") if item.strip()]


def parse_iso_duration_minutes(value: Any) -> int:
    """Parse simple ISO 8601 durations such as PT40M, PT1H20M, PT0S."""
    text = str(value or "").upper().strip()
    if not text:
        return 999

    hour_match = re.search(r"(\d+)H", text)
    minute_match = re.search(r"(\d+)M", text)
    second_match = re.search(r"(\d+)S", text)

    hours = int(hour_match.group(1)) if hour_match else 0
    minutes = int(minute_match.group(1)) if minute_match else 0
    seconds = int(second_match.group(1)) if second_match else 0

    total = hours * 60 + minutes + (1 if seconds > 0 and minutes == 0 and hours == 0 else 0)
    if total == 0:
        # Some source records say PT0S even though the instructions take time.
        return 30
    return total


def format_minutes(minutes: int) -> str:
    if minutes >= 120:
        hours = minutes // 60
        remainder = minutes % 60
        return f"{hours} hr {remainder} min" if remainder else f"{hours} hr"
    return f"{minutes} min"


def detect_meal_type(category: str, keywords: list[str]) -> Literal["Breakfast", "Lunch", "Dinner"]:
    haystack = normalize(" ".join([category, *keywords]))
    if any(word in haystack for word in ["breakfast", "brunch"]):
        return "Breakfast"
    if any(word in haystack for word in ["lunch", "snack", "sandwich", "salad"]):
        return "Lunch"
    return "Dinner"


def detect_cooking_method(category: str, keywords: list[str], instructions: list[str]) -> str:
    haystack = normalize(" ".join([category, *keywords, *instructions[:3]]))
    method_keywords = [
        ("bake", "Bake"),
        ("oven", "Oven"),
        ("grill", "Grill"),
        ("fry", "Pan-fry"),
        ("saute", "Sauté"),
        ("stir fry", "Stir-fry"),
        ("boil", "Boil"),
        ("steam", "Steam"),
        ("slow cooker", "Slow cook"),
        ("pressure", "Pressure cook"),
        ("no cook", "No-cook"),
    ]
    for keyword, label in method_keywords:
        if keyword in haystack:
            return label
    return "Cook"


def normalise_recipe(row: dict[str, Any], index: int) -> dict[str, Any]:
    ingredients = parse_r_vector(row.get("RecipeIngredientParts", ""))
    instructions = parse_r_vector(row.get("RecipeInstructions", ""))
    keywords = parse_r_vector(row.get("Keywords", ""))

    category = str(row.get("RecipeCategory", "") or "")
    minutes = parse_iso_duration_minutes(row.get("TotalTime", ""))
    meal_type = detect_meal_type(category, keywords)
    cooking_method = detect_cooking_method(category, keywords, instructions)

    # Keep matching forgiving: the UI ranks by these core ingredients.
    core_ingredients = ingredients[:6] if ingredients else keywords[:6]

    recipe_name = str(row.get("Name", "") or f"Recipe {index + 1}").strip()

    return {
        "id": index + 1,
        "name": recipe_name,
        "mealType": meal_type,
        "sourceCategory": category,
        "keywords": keywords,
        "prepTime": "10 min",
        "cookTime": format_minutes(max(minutes - 10, 5)),
        "totalTime": format_minutes(minutes),
        "timeMinutes": minutes,
        "cookingMethod": cooking_method,
        "coreIngredients": core_ingredients,
        "allIngredients": ingredients,
        "instructions": instructions,
        "calories": row.get("Calories", ""),
    }


def load_recipes() -> list[dict[str, Any]]:
    if not RECIPES_PATH.exists():
        raise RuntimeError(f"Missing recipe database: {RECIPES_PATH}")

    recipes: list[dict[str, Any]] = []
    with RECIPES_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader):
            recipe = normalise_recipe(row, index)
            if recipe["name"]:
                recipes.append(recipe)

    return recipes


RECIPES = load_recipes()
RECIPE_BY_ID = {recipe["id"]: recipe for recipe in RECIPES}
VECTOR_STORE = RecipeVectorStore(BASE_DIR)


def parse_minutes(value: Any) -> int:
    match = re.search(r"(\d+)", str(value))
    return int(match.group(1)) if match else 999


def recipe_matches(recipe: dict[str, Any], pantry: list[str]) -> dict[str, Any]:
    normalised_pantry = [normalize(item) for item in pantry if str(item).strip()]
    core = recipe.get("coreIngredients", [])

    def has_match(keyword: str) -> bool:
        keyword_norm = normalize(keyword)
        return any(keyword_norm in item or item in keyword_norm for item in normalised_pantry)

    matched = [ingredient for ingredient in core if has_match(ingredient)] if normalised_pantry else []
    missing = [ingredient for ingredient in core if not has_match(ingredient)] if normalised_pantry else []

    total = len(core) or 1
    score = len(matched) / total if normalised_pantry else 0
    tier = 1 if normalised_pantry and not missing else 2 if normalised_pantry and len(missing) <= 1 else 3

    all_ingredients = recipe.get("allIngredients", [])
    available_lines = [
        ingredient
        for ingredient in all_ingredients
        if any(normalize(keyword) in normalize(ingredient) for keyword in matched)
    ]
    missing_lines = [ingredient for ingredient in all_ingredients if ingredient not in available_lines]

    return {
        **recipe,
        "matched": matched,
        "missing": missing,
        "score": score,
        "tier": tier,
        "availLines": available_lines,
        "missingLines": missing_lines,
    }


def search_recipe_database(
    pantry: list[str],
    meal_filter: str = "All",
    name_query: str = "",
    max_time_minutes: int | None = None,
) -> list[dict[str, Any]]:
    candidate_ids = (
        VECTOR_STORE.search_ids(
            pantry=pantry,
            meal_filter=meal_filter,
            name_query=name_query,
            max_time_minutes=max_time_minutes,
        )
        if pantry or name_query.strip()
        else []
    )

    recipes = (
        [RECIPE_BY_ID[recipe_id] for recipe_id in candidate_ids if recipe_id in RECIPE_BY_ID]
        if candidate_ids
        else RECIPES
    )

    if meal_filter != "All":
        recipes = [recipe for recipe in recipes if recipe.get("mealType") == meal_filter]

    if max_time_minutes is not None:
        recipes = [recipe for recipe in recipes if recipe.get("timeMinutes", 999) <= max_time_minutes]

    ranked = [recipe_matches(recipe, pantry) for recipe in recipes]

    if pantry:
        ranked.sort(
            key=lambda item: (
                -len(item.get("matched", [])),
                -item.get("score", 0),
                len(item.get("missing", [])),
                item.get("timeMinutes", 999),
                item.get("name", ""),
            )
        )
    elif not name_query.strip():
        ranked.sort(key=lambda item: (item.get("mealType", ""), item.get("name", "")))

    return ranked


def extract_pantry_from_message(message: str) -> list[str]:
    message = message.lower()
    for prefix in ["with", "using", "i have", "ingredients are", "ingredients:"]:
        if prefix in message:
            message = message.split(prefix, 1)[1]
            break

    pieces = re.split(r",| and |\+|/|\n", message)
    cleaned = []
    ignored = {"what can i make", "can i make", "make", "cook", "recipe", "recipes", "food"}
    for piece in pieces:
        item = normalize(piece)
        item = re.sub(r"\b(what|can|i|make|cook|with|using|have|please|recipe|recipes|food)\b", "", item)
        item = re.sub(r"\s+", " ", item).strip()
        if item and item not in ignored:
            cleaned.append(item)
    return cleaned


OFF_TOPIC_REPLY = (
    "I can only help with LetThemCook cooking questions — recipes, ingredients, "
    "food storage, substitutions, meal planning, and reducing food waste. 🍳\n\n"
    "Try asking: `How to make Filipino Breakfast Steak?` or "
    "`What can I make with eggs, butter, and rice?`"
)

NO_MATCH_REPLY = (
    "I could not find that exact recipe in LetThemCook yet. "
    "Try searching another dish name or list ingredients with commas, like: "
    "eggs, butter, rice. 😊"
)

COOKING_TOPIC_WORDS = {
    "recipe", "recipes", "cook", "cooking", "make", "bake", "fry", "boil", "steam",
    "grill", "saute", "sauté", "meal", "breakfast", "lunch", "dinner", "snack",
    "ingredient", "ingredients", "pantry", "food", "dish", "leftover", "leftovers",
    "store", "storage", "substitute", "replace", "freeze", "thaw", "safe", "safety",
    "waste", "spoil", "expired", "expiry", "calories", "prep", "steps", "instruction",
    "instructions", "filipino", "pandesal", "bistek", "adobo", "sinigang", "rice",
    "egg", "eggs", "butter", "chicken", "beef", "pork", "fish", "vegetable", "vegetables",
    "garlic", "onion", "tomato", "herbs", "herb", "oil", "flour", "milk", "sugar",
    "letthemcook", "database", "dataset", "csv", "mock",
}


def is_let_them_cook_topic(user_message: str) -> bool:
    """Keep Ollama scoped to LetThemCook/cooking before the model is called."""
    cleaned = normalize(user_message)
    if not cleaned:
        return True
    if cleaned in GREETING_WORDS:
        return True

    tokens = set(cleaned.split())
    if tokens & COOKING_TOPIC_WORDS:
        return True

    # Dish-name queries can be only 1–3 words, e.g. "pandesal" or "breakfast steak".
    if search_recipes_by_name(cleaned):
        return True

    return False


def build_ollama_prompt(user_message: str, recipes: list[dict[str, Any]]) -> str:
    context = []
    for recipe in recipes[:3]:
        context.append(
            {
                "name": recipe.get("name"),
                "mealType": recipe.get("mealType"),
                "sourceCategory": recipe.get("sourceCategory"),
                "totalTime": recipe.get("totalTime"),
                "coreIngredients": recipe.get("coreIngredients"),
                "allIngredients": recipe.get("allIngredients", [])[:12],
                "matched": recipe.get("matched", []),
                "missing": recipe.get("missing", []),
                "instructions": recipe.get("instructions", [])[:6],
            }
        )

    context_text = json.dumps(context, ensure_ascii=False, indent=2)

    return f"""
You are LetThemCook Kitchen AI, a local Filipino recipe and food-waste assistant.

STRICT SCOPE:
- Answer only about LetThemCook, recipes, ingredients, substitutions, food storage, meal planning, cooking steps, and reducing food waste.
- If the user asks about anything unrelated, reply exactly: "I can only help with LetThemCook cooking questions — recipes, ingredients, storage, substitutions, and meal planning. 🍳"

LETTHEMCOOK GROUNDING RULES:
- Use ONLY the Recipe Context below for recipe-specific answers.
- Do NOT invent recipes, ingredients, cooking times, or steps that are not present in the context.
- If the context does not contain a matching recipe, say you could not find it in LetThemCook and ask the user to try another dish or list ingredients.
- When a recipe is found, name it naturally, mention the time if available, list the main ingredients, and give clear first steps from the stored instructions.
- If ingredients are missing, say what is missing. Do not pretend the user has everything.
- Do NOT tell the user that the answer came from a database, dataset, CSV, file, or mock data.
- Be friendly, concise, and use plain text. Do not output JSON.

User message:
{user_message}

Recipe Context:
{context_text}
""".strip()


def call_ollama(user_message: str, recipes: list[dict[str, Any]]) -> str | None:
    if not USE_OLLAMA:
        return None

    prompt = build_ollama_prompt(user_message, recipes)

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "top_p": 0.8,
                    "num_predict": 450,
                },
            },
            timeout=OLLAMA_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        reply = (data.get("response") or "").strip()
        return reply or None
    except Exception:
        return None

def fallback_chat_reply(user_message: str, recipes: list[dict[str, Any]]) -> str:
    if "database" in user_message.lower() or "csv" in user_message.lower() or "dataset" in user_message.lower():
        return f"I use the LetThemCook recipe collection. It currently has {len(RECIPES)} recipe records."

    if not recipes:
        return (
            "I could not find a matching recipe yet. Try adding simple ingredients like "
            "eggs, rice, chicken, garlic, onion, or butter. 🍳"
        )

    best = recipes[0]
    missing = best.get("missing", [])
    instructions = best.get("instructions", [])[:3]

    if best.get("score", 0) == 0:
        return (
            "I found recipe options, but none clearly match those ingredients yet. "
            "Try listing your ingredients with commas, like: eggs, butter, rice. 😊"
        )

    if missing:
        missing_text = ", ".join(missing[:4])
        steps = "\n- ".join(instructions) if instructions else "Check the recipe card for steps."
        return (
            f"A good match is {best['name']}. You already match "
            f"{len(best.get('matched', []))}/{len(best.get('coreIngredients', []))} key ingredients. "
            f"You may still need: {missing_text}. 🍳\n\n"
            f"First steps:\n- {steps}"
        )

    steps = "\n- ".join(instructions) if instructions else "Check the recipe card for steps."
    return (
        f"You can make {best['name']} with what you have! ✅ "
        f"It takes about {best.get('totalTime', 'a short time')}.\n\n"
        f"Steps:\n- {steps}"
    )


GREETING_WORDS = {"hi", "hello", "hey", "yo", "good morning", "good afternoon", "good evening"}


def answer_common_cooking_question(user_message: str) -> str | None:
    """Handle common chat intents that are not recipe-search questions."""
    cleaned = normalize(user_message)
    compact = f" {cleaned} "

    if cleaned in GREETING_WORDS or cleaned.startswith(("hello ", "hi ", "hey ")):
        return (
            "Hi! I’m Kitchen AI. 👋\n\n"
            "You can ask me things like:\n"
            "- What can I make with eggs, butter, and rice?\n"
            "- I want to make pandesal\n"
            "- How do I store leftover herbs?"
        )

    if "store" in compact and "herb" in compact:
        return (
            "For leftover herbs: 🌿\n"
            "- Soft herbs like parsley/cilantro: trim the stems, place them in a glass with a little water, loosely cover, then refrigerate.\n"
            "- Basil: keep it at room temperature in a small glass of water.\n"
            "- Hardy herbs like rosemary/thyme: wrap in a slightly damp paper towel and keep in a sealed container or bag in the fridge.\n"
            "- For longer storage, chop and freeze herbs in an ice cube tray with water or oil."
        )

    if "substitute" in compact and "oil" in compact and "butter" in compact:
        return (
            "Yes, but it depends on the recipe. 🧈\n\n"
            "For sautéing or frying, oil can usually replace butter 1:1. "
            "For baking, use about 3/4 cup oil for every 1 cup butter because butter has water and milk solids. "
            "The texture and flavor may be different, so butter is still better for breads, cookies, and pastries when flavor matters."
        )

    if "how long" in compact and "leftover" in compact:
        return (
            "Most cooked leftovers are best kept in the fridge for 3–4 days in a covered container. "
            "Cool them first, refrigerate within 2 hours, and reheat until steaming hot."
        )

    return None


def looks_like_ingredient_request(user_message: str) -> bool:
    """Return True when the user is asking based on ingredients/pantry."""
    text = f" {normalize(user_message)} "
    ingredient_markers = [
        " with ",
        " using ",
        " i have ",
        " i only have ",
        " ingredients ",
        " ingredient ",
        " pantry ",
    ]
    if any(marker in text for marker in ingredient_markers):
        return True

    # Plain comma-separated ingredient list: "eggs, butter, rice".
    if "," in user_message and len([p for p in user_message.split(",") if p.strip()]) >= 2:
        return True

    return False


def extract_recipe_name_query(user_message: str) -> str:
    """Extract a dish/recipe name from messages like 'I want to make pandesal'."""
    if looks_like_ingredient_request(user_message):
        return ""

    text = normalize(user_message)
    if not text or text in GREETING_WORDS:
        return ""

    # Remove common chat/request words but keep the likely dish name.
    text = re.sub(
        r"\b(i|im|i m|want|wanna|would|like|to|make|cook|bake|prepare|recipe|recipes|dish|food|please|can|could|you|give|me|show|tell|how|do|for|a|an|the|of)\b",
        " ",
        text,
    )
    text = re.sub(r"\s+", " ", text).strip()

    # Avoid treating general advice questions as dish names.
    advice_words = {"store", "leftover", "substitute", "replace", "freeze", "thaw", "safe", "safety"}
    tokens = text.split()
    if any(token in advice_words for token in tokens):
        return ""

    # Dish names are usually short. If the remaining text is too long, it is
    # probably not a recipe-name search.
    if 1 <= len(tokens) <= 5:
        return text
    return ""


def recipe_name_alternatives(query: str) -> list[str]:
    query = normalize(query)
    alternatives = [query]

    # Common spelling variants in Filipino recipe names.
    aliases = {
        "pandesal": ["pan de sal"],
        "pan de sal": ["pandesal"],
        "bibingka": ["bigingka"],
        "bigingka": ["bibingka"],
    }
    for key, values in aliases.items():
        if key in query:
            alternatives.extend(values)

    # Keep unique values in order.
    unique: list[str] = []
    for item in alternatives:
        if item and item not in unique:
            unique.append(item)
    return unique


def search_recipes_by_name(query: str) -> list[dict[str, Any]]:
    alternatives = recipe_name_alternatives(query)
    query_tokens = [token for token in normalize(query).split() if len(token) > 1]
    matches: list[dict[str, Any]] = []

    for recipe in RECIPES:
        name = normalize(recipe.get("name", ""))
        direct_match = any(alt and alt in name for alt in alternatives)
        token_match = bool(query_tokens) and all(token in name for token in query_tokens)
        if direct_match or token_match:
            matches.append(recipe_matches(recipe, []))

    matches.sort(key=lambda item: (item.get("timeMinutes", 999), item.get("name", "")))
    return matches


def recipe_detail_reply(recipe: dict[str, Any], all_matches: list[dict[str, Any]] | None = None) -> str:
    ingredients = recipe.get("allIngredients", [])[:8]
    raw_steps = recipe.get("instructions", [])[:4]
    steps = [re.sub(r"^\s*\d+[\.\)]\s*", "", str(step)).strip() for step in raw_steps]

    ingredient_text = ", ".join(ingredients) if ingredients else "ingredients listed in the recipe card"
    step_text = "\n".join(f"{index + 1}. {step}" for index, step in enumerate(steps)) if steps else "Open the recipe card to view the steps."

    reply = (
        f"Here's a recipe you can try: {recipe.get('name')} ✅\n\n"
        f"Estimated time: about {recipe.get('totalTime', 'N/A')}\n"
        f"Main ingredients: {ingredient_text}\n\n"
        f"First steps:\n{step_text}"
    )

    other_matches = [item.get("name") for item in (all_matches or [])[1:4]]
    if other_matches:
        reply += "\n\nOther recipe matches: " + "; ".join(other_matches)

    return reply


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "LetThemCook backend is running"}


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "recipes_loaded": len(RECIPES),
        "database_file": str(RECIPES_PATH.relative_to(BASE_DIR)),
        "ollama_enabled": USE_OLLAMA,
        "ollama_model": OLLAMA_MODEL,
        "focus_mode": "LetThemCook dataset + cooking only",
        "vector_database": "ChromaDB",
        "chroma_records": VECTOR_STORE.count(),
        "chroma_ready": VECTOR_STORE.count() == len(RECIPES),
        "embedding_model": VECTOR_STORE.embedding_model,
    }


@app.get("/api/recipes/all")
def get_all_recipes() -> dict[str, Any]:
    return {"results": [recipe_matches(recipe, []) for recipe in RECIPES]}


@app.get("/api/recipes/{recipe_id}")
def get_recipe(recipe_id: int) -> dict[str, Any]:
    for recipe in RECIPES:
        if recipe["id"] == recipe_id:
            return {"result": recipe_matches(recipe, [])}
    raise HTTPException(status_code=404, detail="Recipe not found")


@app.post("/api/recipes/search")
def search_recipes(request: RecipeSearchRequest) -> dict[str, Any]:
    results = search_recipe_database(request.pantry, request.mealFilter, request.nameQuery)
    return {"results": results}


@app.post("/api/chat")
def chat_with_chef_llama(request: ChatRequest) -> dict[str, str]:
    user_message = request.user_message.strip()

    common_reply = answer_common_cooking_question(user_message)
    if common_reply:
        return {"chef_reply": common_reply}

    # Hard guardrail: do not send unrelated questions to Ollama.
    # This keeps the local model focused on LetThemCook and cooking only.
    if not is_let_them_cook_topic(user_message):
        return {"chef_reply": OFF_TOPIC_REPLY}

    if "database" in user_message.lower() or "dataset" in user_message.lower() or "csv" in user_message.lower():
        return {"chef_reply": fallback_chat_reply(user_message, [])}

    # If the user asks for a named dish, search recipe titles first.
    # Example: "How to make breakfast steak?" should find Filipino Breakfast Steak
    # instead of treating "breakfast steak" as pantry ingredients.
    dish_query = extract_recipe_name_query(user_message)
    if dish_query:
        name_matches = search_recipes_by_name(dish_query)
        if name_matches:
            ollama_reply = call_ollama(user_message, name_matches)
            if ollama_reply:
                return {"chef_reply": ollama_reply}
            return {"chef_reply": recipe_detail_reply(name_matches[0], name_matches)}

        # Do not let Llama invent a dish if the dataset has no matching title.
        return {"chef_reply": NO_MATCH_REPLY}

    pantry = extract_pantry_from_message(user_message) if looks_like_ingredient_request(user_message) else []
    if pantry:
        recipes = search_recipe_database(pantry)
        matched_recipes = [recipe for recipe in recipes if recipe.get("score", 0) > 0]

        if matched_recipes:
            ollama_reply = call_ollama(user_message, matched_recipes)
            if ollama_reply:
                return {"chef_reply": ollama_reply}
            return {"chef_reply": fallback_chat_reply(user_message, matched_recipes)}

        return {"chef_reply": NO_MATCH_REPLY}

    return {
        "chef_reply": (
            "I can help, but I need a dish name from LetThemCook or a list of ingredients. "
            "Try: `How to make Filipino Breakfast Steak?` or `eggs, butter, rice`. 🍳"
        )
    }


@app.post("/api/generate-recipe")
def generate_rag_recipe(query: RecipeQuery) -> dict[str, Any]:
    pantry = [item.strip() for item in re.split(r",| and |\+|/|\n", query.user_ingredients) if item.strip()]
    results = search_recipe_database(pantry, max_time_minutes=query.max_time_minutes)
    matched_results = [recipe for recipe in results if recipe.get("score", 0) > 0]

    if matched_results:
        reply = call_ollama(query.user_ingredients, matched_results) or fallback_chat_reply(query.user_ingredients, matched_results)
    else:
        reply = NO_MATCH_REPLY

    return {
        "status": "success",
        "backend_process": "LetThemCook_RAG_Dataset_Grounded",
        "chef_reply": reply,
        "results": matched_results[:3],
    }
