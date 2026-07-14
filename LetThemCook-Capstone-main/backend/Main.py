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
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "180"))

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
                limit=500,
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

    if name_query.strip():
        query = normalize(name_query)
        query_tokens = [token for token in query.split() if len(token) > 1]
        title_matches = [
            recipe
            for recipe in recipes
            if query in normalize(recipe.get("name", ""))
            or (
                query_tokens
                and all(token in normalize(recipe.get("name", "")) for token in query_tokens)
            )
        ]
        if title_matches:
            recipes = title_matches
        elif candidate_ids:
            # Keep only the strongest semantic alternatives when there is no
            # literal title match.
            recipes = recipes[:50]
        else:
            recipes = []

    ranked = [recipe_matches(recipe, pantry) for recipe in recipes]

    if pantry:
        # Do not return unrelated recipes when none of the user's ingredients match.
        ranked = [item for item in ranked if item.get("matched")]
        ranked.sort(
            key=lambda item: (
                item.get("tier", 3),
                -item.get("score", 0),
                len(item.get("missing", [])),
                -len(item.get("matched", [])),
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
    prefix_positions = [
        (message.find(prefix), prefix)
        for prefix in ["i have", "ingredients are", "ingredients:", "using", "with"]
        if prefix in message
    ]
    if prefix_positions:
        _, first_prefix = min(prefix_positions, key=lambda item: item[0])
        message = message.split(first_prefix, 1)[1]

    pieces = re.split(r",| and | with |\+|/|\n", message)
    cleaned = []
    ignored = {"what can i make", "can i make", "make", "cook", "recipe", "recipes", "food"}
    for piece in pieces:
        item = normalize(piece)
        item = re.sub(r"\b(what|can|i|make|cook|with|using|have|please|recipe|recipes|food)\b", "", item)
        item = re.sub(r"\s+", " ", item).strip()
        if item and item not in ignored:
            cleaned.append(item)
    return cleaned



NO_MATCH_REPLY = (
    "I could not find that exact recipe in LetThemCook yet. "
    "Try searching another dish name or list ingredients with commas, like: "
    "eggs, butter, rice. 😊"
)




STRUCTURED_RECIPE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "dish_name": {"type": "string"},
        "used_ingredients": {"type": "array", "items": {"type": "string"}},
        "missing_ingredients": {"type": "array", "items": {"type": "string"}},
        "assumed_staples": {"type": "array", "items": {"type": "string"}},
        "execution_steps": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "dish_name",
        "used_ingredients",
        "missing_ingredients",
        "assumed_staples",
        "execution_steps",
    ],
    "additionalProperties": False,
}


def build_system_prompt(recipes: list[dict[str, Any]], structured: bool = False) -> str:
    context = []
    for recipe in recipes[:3]:
        context.append(
            {
                "name": recipe.get("name"),
                "category": recipe.get("sourceCategory"),
                "totalTime": recipe.get("totalTime"),
                "allIngredients": recipe.get("allIngredients", []),
                "matched": recipe.get("matched", []),
                "missing": recipe.get("missing", []),
                "unusedPantry": recipe.get("unusedPantry", []),
                "instructions": recipe.get("instructions", []),
            }
        )

    context_text = json.dumps(context, ensure_ascii=False, indent=2)

    if structured:
        response_rule = """
STRUCTURED RECIPE OUTPUT:
- Select one recipe from Recipe Context.
- Return only one JSON object that follows the supplied schema.
- Copy the selected database recipe name exactly.
- Do not add ingredients or cooking steps that are absent from that record.
- Do not wrap the JSON in Markdown or add conversational text.
""".strip()
    else:
        response_rule = """
CONVERSATIONAL OUTPUT:
- Reply in clear, friendly plain text. Never display raw JSON in chat.
- When Recipe Context contains matches, base every recipe name, ingredient,
  cooking time, and instruction on one of those records.
- Do not merge multiple database recipes or invent a replacement recipe.
- When Recipe Context is empty, you may answer general cooking, storage, or
  substitution questions, but do not claim that a specific recipe is in the
  LetThemCook database.
""".strip()

    return f"""
You are Chef LetThemCook, a warm and skilled culinary assistant.

DATABASE GROUNDING RULES:
- Recipe Context is the only authority for specific LetThemCook recipes.
- Treat every context field as read-only database evidence.
- Never invent a database recipe, ingredient, cooking time, or instruction.
- If the requested recipe is absent, say that no database match was found.

{response_rule}

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
    structured: bool = False,
) -> str | None:
    """Send a grounded chat request to the local Llama model."""
    if not USE_OLLAMA:
        return None

    system_prompt = build_system_prompt(recipes, structured=structured)

    # Ollama chat uses one ordered message list. The system prompt comes first,
    # then the previous conversation, then the newest user message.
    messages = [{"role": "system", "content": system_prompt}]
    for message in history or []:
        messages.append({"role": message.role, "content": message.content})
    messages.append({"role": "user", "content": user_message})

    request_payload: dict[str, Any] = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            # Lower randomness helps Llama follow the retrieved recipe exactly.
            "temperature": 0.0 if structured else 0.2,
            "top_p": 0.85,
        },
    }
    if structured:
        request_payload["format"] = STRUCTURED_RECIPE_SCHEMA

    try:
        response = requests.post(
            get_ollama_chat_url(),
            json=request_payload,
            timeout=OLLAMA_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        reply = (data.get("message", {}).get("content") or "").strip()
        if structured and reply:
            grounded_payload = validate_structured_recipe_reply(reply, recipes)
            if grounded_payload is None:
                print("Ollama returned recipe JSON that was not grounded in the retrieved records.")
                return None
            return json.dumps(grounded_payload, ensure_ascii=False)
        return reply or None
    except requests.RequestException as error:
        # Returning None lets the existing database fallback answer safely.
        print(f"Ollama is unavailable or timed out: {error}")
        return None
    except (TypeError, ValueError) as error:
        print(f"Ollama returned an invalid response: {error}")
        return None


def structured_recipe_payload(recipe: dict[str, Any]) -> dict[str, Any]:
    """Build the frontend recipe contract exclusively from one database row."""
    ingredients = [str(item) for item in recipe.get("allIngredients", []) if str(item).strip()]
    steps = [str(item) for item in recipe.get("instructions", []) if str(item).strip()]
    matched = [str(item) for item in recipe.get("matched", []) if str(item).strip()]
    missing = [str(item) for item in recipe.get("missing", []) if str(item).strip()]
    staples = [item for item in ingredients if is_basic_staple(item)]

    return {
        "dish_name": str(recipe.get("name", "Database Recipe")),
        "used_ingredients": matched,
        "missing_ingredients": missing,
        "assumed_staples": staples,
        "execution_steps": steps,
    }


def validate_structured_recipe_reply(
    reply: str,
    recipes: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Accept the model's selection only when it names a retrieved recipe.

    The returned details are rebuilt from the selected database record. This
    prevents a syntactically valid model response from adding unsupported facts.
    """
    text = reply.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)

    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        return None

    try:
        payload = json.loads(text[start : end + 1])
        if isinstance(payload, str):
            payload = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None

    selected_name = normalize(payload.get("dish_name", ""))
    recipe_by_name = {
        normalize(recipe.get("name", "")): recipe
        for recipe in recipes
        if recipe.get("name")
    }
    selected_recipe = recipe_by_name.get(selected_name)
    if selected_recipe is None:
        return None

    return structured_recipe_payload(selected_recipe)


def fallback_chat_reply(user_message: str, matched_recipes: list[dict]) -> str:
    """
    Emergency Fallback: Mimics the exact JSON structure of Llama 3.2.
    Prevents the React frontend from crashing if the AI engine goes offline.
    """
    # Scenario A: AI is off AND no recipes match the pantry
    if not matched_recipes:
        fallback_data = {
            "dish_name": "No Database Match",
            "used_ingredients": [],
            "missing_ingredients": [],
            "assumed_staples": [],
            "execution_steps": [
                "LetThemCook could not find a database recipe matching those ingredients.",
                "Try another dish name or enter ingredients separated by commas.",
            ]
        }
        return json.dumps(fallback_data, ensure_ascii=False)

    # Scenario B: AI is off, but ChromaDB found a RAG match!
    top_recipe = matched_recipes[0]
    return json.dumps(structured_recipe_payload(top_recipe), ensure_ascii=False)




GREETINGS = {
    "hello",
    "hi",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
    "how are you",
    "yo",
}

ADVICE_WORDS = {
    "store",
    "leftover",
    "substitute",
    "replace",
    "freeze",
    "thaw",
    "safe",
    "safety",
    "scale",
}


def is_greeting(text: str) -> bool:
    normalized_text = normalize(text)
    return normalized_text in GREETINGS or any(
        normalized_text.startswith(greeting + " ") for greeting in GREETINGS
    )


def looks_like_ingredient_request(text: str) -> bool:
    """Return True when a message appears to provide pantry ingredients."""
    lowered = text.lower()
    if any(word in normalize(text).split() for word in ADVICE_WORDS):
        return False
    return any(
        marker in lowered
        for marker in [",", " and ", " with ", " using ", "i have ", "ingredients:"]
    )


def extract_recipe_name_query(user_message: str) -> str:
    """Extract a dish/recipe name from messages like 'I want to make pandesal'."""
    if looks_like_ingredient_request(user_message):
        return ""

    if is_greeting(user_message):
        return ""

    text = normalize(user_message)
    if not text:
        return ""

    # Remove common chat/request words but keep the likely dish name.
    text = re.sub(
        r"\b(i|im|i m|want|wanna|would|like|to|make|cook|bake|prepare|recipe|recipes|dish|food|please|can|could|you|give|me|show|tell|how|do|for|a|an|the|of)\b",
        " ",
        text,
    )
    text = re.sub(r"\s+", " ", text).strip()

    # Avoid treating general advice questions as dish names.
    tokens = text.split()
    if any(token in ADVICE_WORDS for token in tokens):
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


def general_chat_fallback(user_message: str) -> str:
    """Return readable chat text when the local language model is unavailable."""
    if is_greeting(user_message):
        return "Hello! Tell me what ingredients you have, and I will search the LetThemCook recipe database."
    return (
        "The local cooking AI is currently unavailable. "
        "Recipe searches still use the LetThemCook database, so try entering a dish name "
        "or a comma-separated ingredient list."
    )


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
        return {"chef_reply": "Please enter a message or a recipe name. 🍳"}

    # Search the database before the language model sees a recipe request.
    dish_query = extract_recipe_name_query(user_message)
    matched_recipes: list[dict[str, Any]] = []
    ingredient_request = looks_like_ingredient_request(user_message)

    if dish_query:
        matched_recipes = search_recipes_by_name(dish_query)
        if not matched_recipes:
            return {"chef_reply": NO_MATCH_REPLY}
    elif ingredient_request:
        pantry = extract_pantry_from_message(user_message)
        if pantry:
            matched_recipes = search_recipe_database(pantry)
            matched_recipes = [recipe for recipe in matched_recipes if recipe.get("score", 0) > 0]
        if not matched_recipes:
            return {"chef_reply": NO_MATCH_REPLY}

    # The model receives only the retrieved rows plus real chat history.
    ollama_reply = call_ollama(user_message, matched_recipes, history)

    if ollama_reply:
        return {"chef_reply": ollama_reply}

    if matched_recipes:
        return {"chef_reply": recipe_detail_reply(matched_recipes[0], matched_recipes)}
    return {"chef_reply": general_chat_fallback(user_message)}


@app.post("/api/generate-recipe")
def generate_rag_recipe(query: RecipeQuery) -> dict[str, Any]:
    pantry = [item.strip() for item in re.split(r",| and |\+|/|\n", query.user_ingredients) if item.strip()]
    results = search_recipe_database(pantry, max_time_minutes=query.max_time_minutes)
    matched_results = [recipe for recipe in results if recipe.get("score", 0) > 0]

    if matched_results:
        reply = call_ollama(
            query.user_ingredients,
            matched_results,
            structured=True,
        ) or fallback_chat_reply(query.user_ingredients, matched_results)
    else:
        reply = fallback_chat_reply(query.user_ingredients, [])

    return {
        "status": "success",
        "backend_process": "LetThemCook_RAG_Dataset_Grounded",
        "chef_reply": reply,
        "results": matched_results[:3],
    }
