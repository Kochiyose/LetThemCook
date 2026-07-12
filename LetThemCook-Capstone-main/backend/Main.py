"""LetThemCook FastAPI backend.

The app uses a local CSV recipe catalog, ChromaDB semantic search, and Ollama.
It exposes the results to the React/Vite UI through REST endpoints. When a local
AI service is unavailable, safe CSV fallbacks keep the recipe catalog usable.
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


def env_flag(name: str, default: bool = False) -> bool:
    """Read a true/false value from the environment.

    Accepted true values: true, 1, yes, and on. This keeps the .env file easy
    for the group to edit without changing Python code.
    """
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"true", "1", "yes", "on"}


# These values come from backend/.env. The code no longer ignores the group
# configuration. We use the exact 3B model tag promised in the proposal.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_URL = os.getenv("OLLAMA_URL", f"{OLLAMA_BASE_URL}/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
USE_OLLAMA = env_flag("USE_OLLAMA", True)
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "45"))

app = FastAPI(title="LetThemCook Backend API", version="1.3.0")

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


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    user_message: str
    history: list[ChatMessage] = Field(default_factory=list)  # Previous chat messages sent by React


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


def parse_recipe_minutes(value: Any) -> int:
    """Convert the CSV time value into minutes.

    The cleaned LetThemCook CSV stores plain numbers such as 50. Older copies
    may still use ISO values such as PT1H20M, so this function supports both.
    """
    text = str(value or "").upper().strip()
    if not text:
        return 999

    # Current CSV format: TotalTime_Mins contains values such as 30 or 45.
    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        return max(1, int(float(text)))

    # Older dataset format: PT40M, PT1H20M, or PT0S.
    hour_match = re.search(r"(\d+)H", text)
    minute_match = re.search(r"(\d+)M", text)
    second_match = re.search(r"(\d+)S", text)

    hours = int(hour_match.group(1)) if hour_match else 0
    minutes = int(minute_match.group(1)) if minute_match else 0
    seconds = int(second_match.group(1)) if second_match else 0

    total = hours * 60 + minutes + (1 if seconds > 0 and minutes == 0 and hours == 0 else 0)
    if total == 0:
        # Some old source records use PT0S even when cooking still takes time.
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
    minutes = parse_recipe_minutes(row.get("TotalTime_Mins", ""))
    meal_type = detect_meal_type(category, keywords)
    cooking_method = detect_cooking_method(category, keywords, instructions)

    # Keep the first six items for compact card summaries. Matching now uses the full ingredient list.
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


# Basic staples are allowed by the proposal even when the user does not type them.
# Keep this list short so the recommendation still respects the user's pantry.
BASIC_STAPLES = {
    "water",
    "salt",
    "pepper",
    "black pepper",
    "ground black pepper",
    "cooking oil",
    "vegetable oil",
}


def ingredient_matches_pantry(ingredient: str, pantry_terms: list[str]) -> bool:
    """Return True when one recipe ingredient matches one pantry item.

    The check is intentionally simple and forgiving. For example, "chicken"
    matches "chicken pieces", while "green onion" matches "green onions".
    """
    ingredient_key = normalize(ingredient)

    def phrase_inside(longer: str, shorter: str) -> bool:
        # Word boundaries prevent false matches such as "egg" inside "eggplant".
        return bool(re.search(rf"\b{re.escape(shorter)}\b", longer))

    for pantry_item in pantry_terms:
        if not pantry_item:
            continue
        if phrase_inside(ingredient_key, pantry_item) or phrase_inside(pantry_item, ingredient_key):
            return True

        # Allow a simple singular/plural difference: onion ↔ onions, egg ↔ eggs.
        ingredient_singular = re.sub(r"s$", "", ingredient_key) if len(ingredient_key) > 3 else ingredient_key
        pantry_singular = re.sub(r"s$", "", pantry_item) if len(pantry_item) > 3 else pantry_item
        if phrase_inside(ingredient_singular, pantry_singular) or phrase_inside(pantry_singular, ingredient_singular):
            return True

    return False


def is_basic_staple(ingredient: str) -> bool:
    """Return True for small kitchen staples allowed by the project rules."""
    ingredient_key = normalize(ingredient)
    return any(
        ingredient_key == staple
        or ingredient_key.startswith(staple + " ")
        or ingredient_key.endswith(" " + staple)
        for staple in BASIC_STAPLES
    )


def recipe_matches(recipe: dict[str, Any], pantry: list[str]) -> dict[str, Any]:
    """Calculate recipe match information using the full ingredient list.

    Older code checked only the first six ingredients. This version checks every
    ingredient, excludes approved basic staples from the missing count, and also
    reports pantry items that the selected recipe does not use.
    """
    pantry_terms = [normalize(item) for item in pantry if str(item).strip()]
    all_ingredients = recipe.get("allIngredients", []) or recipe.get("coreIngredients", [])

    if not pantry_terms:
        return {
            **recipe,
            "matched": [],
            "missing": [],
            "score": 0,
            "tier": 3,
            "availLines": [],
            "missingLines": list(all_ingredients),
            "unusedPantry": [],
        }

    available_lines = [
        ingredient
        for ingredient in all_ingredients
        if ingredient_matches_pantry(ingredient, pantry_terms) or is_basic_staple(ingredient)
    ]
    missing_lines = [
        ingredient
        for ingredient in all_ingredients
        if ingredient not in available_lines and not is_basic_staple(ingredient)
    ]

    # "matched" contains the user's real pantry matches only. Basic staples are
    # considered available but are not counted as user-provided ingredients.
    matched = [
        ingredient
        for ingredient in all_ingredients
        if ingredient_matches_pantry(ingredient, pantry_terms)
    ]
    required_ingredients = [
        ingredient for ingredient in all_ingredients if not is_basic_staple(ingredient)
    ]
    score = len(matched) / (len(required_ingredients) or 1)
    tier = 1 if not missing_lines else 2 if len(missing_lines) <= 1 else 3

    unused_pantry = [
        pantry_item
        for pantry_item in pantry
        if not any(
            ingredient_matches_pantry(ingredient, [normalize(pantry_item)])
            for ingredient in all_ingredients
        )
    ]

    return {
        **recipe,
        "matched": matched,
        "missing": missing_lines,
        "score": score,
        "tier": tier,
        "availLines": available_lines,
        "missingLines": missing_lines,
        "unusedPantry": unused_pantry,
    }


def search_recipe_database(
    pantry: list[str],
    meal_filter: str = "All",
    name_query: str = "",
    max_time_minutes: int | None = None,
) -> list[dict[str, Any]]:
    candidate_ids: list[int] = []
    vector_search_failed = False

    if pantry or name_query.strip():
        try:
            # ChromaDB uses the local all-minilm embedding model through Ollama.
            candidate_ids = VECTOR_STORE.search_ids(
                pantry=pantry,
                meal_filter=meal_filter,
                name_query=name_query,
                max_time_minutes=max_time_minutes,
            )
        except Exception as error:
            # Do not crash the whole API when Ollama or the embedding model is off.
            # The backend safely falls back to the local CSV recipe collection.
            vector_search_failed = True
            print(f"ChromaDB search unavailable. Using local CSV fallback: {error}")

    recipes = (
        [RECIPE_BY_ID[recipe_id] for recipe_id in candidate_ids if recipe_id in RECIPE_BY_ID]
        if candidate_ids
        else RECIPES
    )

    # When vector search is unavailable, keep recipe-name search useful by using
    # a simple local title match instead of returning every recipe.
    if vector_search_failed and name_query.strip():
        query = normalize(name_query)
        recipes = [recipe for recipe in recipes if query in normalize(recipe.get("name", ""))]

    if meal_filter != "All":
        recipes = [recipe for recipe in recipes if recipe.get("mealType") == meal_filter]

    if max_time_minutes is not None:
        recipes = [recipe for recipe in recipes if recipe.get("timeMinutes", 999) <= max_time_minutes]

    ranked = [recipe_matches(recipe, pantry) for recipe in recipes]

    if pantry:
        # Do not return unrelated recipes when none of the user's ingredients match.
        ranked = [item for item in ranked if item.get("matched")]
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

    # A pantry search only needs the strongest recommendations. Limiting the
    # response prevents hundreds of cards from slowing down the browser.
    if pantry and not name_query.strip():
        ranked = ranked[:100]

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


def build_system_prompt(recipes: list[dict[str, Any]]) -> str:
    context = []
    for recipe in recipes[:3]:
        context.append(
            {
                "name": recipe.get("name"),
                "totalTime": recipe.get("totalTime"),
                "allIngredients": recipe.get("allIngredients", []),
                "matched": recipe.get("matched", []),
                "missing": recipe.get("missing", []),
                "unusedPantry": recipe.get("unusedPantry", []),
                "instructions": recipe.get("instructions", []),
            }
        )

    context_text = json.dumps(context, ensure_ascii=False, indent=2)

    return f"""
You are LetThemCook Kitchen AI, a friendly, highly conversational Filipino recipe assistant.

GROUNDING RULES:
- For recipe names, ingredients, measurements, and cooking steps, use only the Recipe Context below.
- Never invent a recipe that is not present in the Recipe Context.
- When the Recipe Context is empty, answer only general cooking, storage, substitution, or food-waste questions.
- Do not tell the user that a recipe was "found in the database". Speak naturally as a cooking assistant.
- When unusedPantry has values, briefly tell the user which pantry items are not used by the selected recipe.
- Do not add ingredients, measurements, or steps that are missing from the Recipe Context.

CRITICAL RULES - CONVERSATION PHASES:
You must strictly follow these two phases of conversation. DO NOT jump to Phase 2 until the user explicitly confirms!

PHASE 1: OPTIONS & CONFIRMATION (NO STEPS YET)
- If the user asks for a recipe by name (e.g., "Adobo" or "How to make Sinigang") OR gives ingredients (e.g., "2 eggs"):
- 🚨 NEVER give the recipe steps or ingredient measurements right away! 🚨
- INSTEAD, look at the Recipe Context. If there are multiple matches, present them as options: "I found a few ways to make that! I have [Option 1] and [Option 2]. Which recipe are we going for?"
- If there is only one match, ask for confirmation: "I have a great recipe for [Recipe Name]. Want me to guide you through the steps?"

PHASE 2: EXECUTION (GIVING THE STEPS)
- ONLY enter Phase 2 AFTER the user explicitly chooses an option or says "Yes" to your Phase 1 question.
- Once they confirm (e.g., "Chicken adobo please", "Yes, let's do it"), THEN provide the full ingredient list and step-by-step instructions.
- Be dynamic, supportive, and chatty like a real chef.

Recipe Context:
{context_text}
""".strip()


def get_ollama_chat_url() -> str:
    """Return the Ollama chat endpoint even if .env uses /api/generate."""
    url = OLLAMA_URL.rstrip("/")
    if url.endswith("/api/generate"):
        return url[: -len("/api/generate")] + "/api/chat"
    if url.endswith("/api/chat"):
        return url
    return url + "/api/chat"


def call_ollama(
    user_message: str,
    recipes: list[dict[str, Any]],
    history: list[ChatMessage] | None = None,
) -> str | None:
    """Send a grounded chat request to the local Llama model."""
    if not USE_OLLAMA:
        return None

    system_prompt = build_system_prompt(recipes)

    # Ollama chat uses one ordered message list. The system prompt comes first,
    # then the previous conversation, then the newest user message.
    messages = [{"role": "system", "content": system_prompt}]
    for message in history or []:
        messages.append({"role": message.role, "content": message.content})
    messages.append({"role": "user", "content": user_message})

    try:
        response = requests.post(
            get_ollama_chat_url(),
            json={
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "options": {
                    # Lower randomness helps Llama follow the retrieved recipe exactly.
                    "temperature": 0.2,
                    "top_p": 0.85,
                },
            },
            timeout=OLLAMA_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        reply = (data.get("message", {}).get("content") or "").strip()
        return reply or None
    except requests.RequestException as error:
        # Returning None lets the existing database fallback answer safely.
        print(f"Ollama is unavailable or timed out: {error}")
        return None
    except (TypeError, ValueError) as error:
        print(f"Ollama returned an invalid response: {error}")
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
        " just ", # Added for phrases like "just eggs"
    ]
    if any(marker in text for marker in ingredient_markers):
        return True

    # Plain comma-separated ingredient list: "eggs, butter, rice".
    if "," in user_message and len([p for p in user_message.split(",") if p.strip()]) >= 2:
        return True
        
    # FIX: If the message is very short (1-3 words) and contains a basic ingredient, treat it as a pantry request.
    basic_ingredients = {"egg", "eggs", "rice", "chicken", "pork", "beef", "fish", "garlic", "onion"}
    tokens = set(normalize(user_message).split())
    if len(tokens) <= 3 and tokens & basic_ingredients:
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
    # Use the complete stored recipe when Ollama is unavailable.
    ingredients = recipe.get("allIngredients", [])
    raw_steps = recipe.get("instructions", [])
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


def recipe_confirmation_reply(recipes: list[dict[str, Any]]) -> str:
    """Ask the user to choose or confirm before showing full instructions.

    This is the safe non-AI fallback for Phase 1. It keeps the same chat flow even
    when Ollama is stopped or still loading.
    """
    if not recipes:
        return NO_MATCH_REPLY

    names = [str(recipe.get("name", "Recipe")) for recipe in recipes[:3]]
    if len(names) == 1:
        return f"I have a recipe for {names[0]}. Want me to guide you through the steps? 🍳"

    options = "\n".join(f"{index + 1}. {name}" for index, name in enumerate(names))
    return (
        "Here are the closest recipe options:\n"
        f"{options}\n\n"
        "Which recipe would you like to make?"
    )


CONFIRMATION_WORDS = {
    "yes", "yes please", "sure", "okay", "ok", "continue", "go ahead",
    "show me", "show the steps", "give me the steps", "lets do it", "let s do it",
}


def is_confirmation_message(user_message: str) -> bool:
    """Detect short replies that continue the previous recipe conversation."""
    return normalize(user_message) in CONFIRMATION_WORDS


def recipes_mentioned_in_history(history: list[ChatMessage]) -> list[dict[str, Any]]:
    """Find recipe names mentioned in recent assistant replies.

    React sends the previous chat messages. We scan those messages for recipe
    names so a reply such as "Yes" can continue with the correct recipe.
    """
    recent_text = " ".join(message.content for message in history[-6:] if message.role == "assistant")
    normalized_history = normalize(recent_text)
    if not normalized_history:
        return []

    matches = [
        recipe_matches(recipe, [])
        for recipe in RECIPES
        if normalize(recipe.get("name", "")) in normalized_history
    ]
    # Prefer the longest matching title. This avoids choosing a generic title
    # such as "Adobo" when the history says "Classic Filipino Chicken Adobo".
    matches.sort(
        key=lambda item: (
            len(normalize(item.get("name", ""))),
            normalized_history.rfind(normalize(item.get("name", ""))),
        ),
        reverse=True,
    )
    return matches[:3]


def model_name_matches(installed_name: str, requested_name: str) -> bool:
    """Compare Ollama model tags without being confused by :latest."""
    installed = installed_name.strip().lower()
    requested = requested_name.strip().lower()
    if installed == requested:
        return True
    # A model name without a tag (example: all-minilm) may match :latest.
    if ":" not in requested:
        return installed.split(":", 1)[0] == requested
    return False


def get_local_ai_health() -> dict[str, Any]:
    """Check Ollama, required models, and one real ChromaDB query.

    This endpoint is used by the frontend status badge. A stored record count is
    not enough because ChromaDB also needs the embedding model to run a query.
    """
    result: dict[str, Any] = {
        "ollama_ready": False,
        "model_ready": False,
        "embedding_model_ready": False,
        "chroma_query_ready": False,
        "error": None,
    }

    if not USE_OLLAMA:
        result["error"] = "Ollama is disabled in backend/.env"
        return result

    try:
        response = requests.get(
            f"{OLLAMA_BASE_URL}/api/tags",
            timeout=min(5, OLLAMA_TIMEOUT_SECONDS),
        )
        response.raise_for_status()
        models = response.json().get("models", [])
        installed_names = [str(item.get("name") or item.get("model") or "") for item in models]

        result["ollama_ready"] = True
        result["model_ready"] = any(
            model_name_matches(name, OLLAMA_MODEL) for name in installed_names
        )
        result["embedding_model_ready"] = any(
            model_name_matches(name, VECTOR_STORE.embedding_model)
            or name.split(":", 1)[0] == VECTOR_STORE.embedding_model.split(":", 1)[0]
            for name in installed_names
        )

        if result["embedding_model_ready"] and VECTOR_STORE.count() > 0:
            # A one-result query confirms that ChromaDB and the embedding model
            # can work together, not only that database files exist.
            result["chroma_query_ready"] = bool(
                VECTOR_STORE.search_ids([], name_query="adobo", limit=1)
            )
    except Exception as error:
        result["error"] = str(error)

    return result


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "LetThemCook backend is running"}


@app.get("/health")
def health() -> dict[str, Any]:
    """Return the real status used by the frontend connection badge."""
    chroma_records = VECTOR_STORE.count()
    ai_health = get_local_ai_health()
    database_ready = chroma_records == len(RECIPES)
    full_rag_ready = bool(
        database_ready
        and ai_health["ollama_ready"]
        and ai_health["model_ready"]
        and ai_health["chroma_query_ready"]
    )

    return {
        "status": "ok" if full_rag_ready else "degraded",
        "backend_ready": True,
        "recipes_loaded": len(RECIPES),
        "database_file": str(RECIPES_PATH.relative_to(BASE_DIR)),
        "ollama_enabled": USE_OLLAMA,
        "ollama_ready": ai_health["ollama_ready"],
        "ollama_model": OLLAMA_MODEL,
        "model_ready": ai_health["model_ready"],
        "focus_mode": "LetThemCook dataset + cooking only",
        "vector_database": "ChromaDB",
        "chroma_records": chroma_records,
        "chroma_ready": database_ready,
        "chroma_query_ready": ai_health["chroma_query_ready"],
        "embedding_model": VECTOR_STORE.embedding_model,
        "embedding_model_ready": ai_health["embedding_model_ready"],
        "catalog_mode": "local_rag" if full_rag_ready else "local_csv_fallback",
        "health_error": ai_health["error"],
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
    history = request.history

    if not user_message:
        return {"chef_reply": "Please enter a recipe name or ingredient list. 🍳"}

    # Short cooking tips and greetings do not need a database search or Llama.
    common_reply = answer_common_cooking_question(user_message)
    if common_reply:
        return {"chef_reply": common_reply}

    # A reply such as "Yes" should continue the recipe mentioned earlier.
    # We recover that recipe from the chat history sent by the React frontend.
    if history and is_confirmation_message(user_message):
        history_matches = recipes_mentioned_in_history(history)
        if history_matches:
            ollama_reply = call_ollama(user_message, history_matches, history)
            if ollama_reply:
                return {"chef_reply": ollama_reply}
            return {"chef_reply": recipe_detail_reply(history_matches[0], history_matches)}
        return {
            "chef_reply": (
                "Please tell me the recipe name first, then I can guide you through the steps. 🍳"
            )
        }

    # Stop unrelated questions before they reach Llama. This keeps the model
    # focused on LetThemCook, recipes, pantry use, and food-waste topics.
    if not is_let_them_cook_topic(user_message):
        return {"chef_reply": OFF_TOPIC_REPLY}

    dish_query = extract_recipe_name_query(user_message)
    if dish_query:
        name_matches = search_recipes_by_name(dish_query)
        if name_matches:
            ollama_reply = call_ollama(user_message, name_matches, history)
            if ollama_reply:
                return {"chef_reply": ollama_reply}
            return {"chef_reply": recipe_confirmation_reply(name_matches)}
        return {"chef_reply": NO_MATCH_REPLY}

    pantry = extract_pantry_from_message(user_message) if looks_like_ingredient_request(user_message) else []
    if pantry:
        recipes = search_recipe_database(pantry)
        matched_recipes = [recipe for recipe in recipes if recipe.get("score", 0) > 0]

        if matched_recipes:
            ollama_reply = call_ollama(user_message, matched_recipes, history)
            if ollama_reply:
                return {"chef_reply": ollama_reply}
            return {"chef_reply": recipe_confirmation_reply(matched_recipes)}

        # Do not ask Llama to invent a recipe when the database has no match.
        return {"chef_reply": NO_MATCH_REPLY}

    # General cooking questions can still use local Llama, but the system prompt
    # tells it not to invent a recipe that is missing from the Recipe Context.
    ollama_reply = call_ollama(user_message, [], history)
    if ollama_reply:
        return {"chef_reply": ollama_reply}

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
