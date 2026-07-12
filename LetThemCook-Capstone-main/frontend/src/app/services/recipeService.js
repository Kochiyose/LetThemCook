/**
 * Recipe service
 * --------------
 * Primary source: FastAPI + ChromaDB + backend/data/LetThemCook_Cleaned.csv.
 * Safe fallback: local recipes.mock.json when the backend cannot be reached.
 *
 * The service returns the source name so App.jsx can show whether the page is
 * using the real local backend or only the offline frontend catalog.
 */

import { RECIPE_DATABASE } from "../data/recipes.js";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

// These small staples are allowed by the project even when the user does not
// type them in the pantry. Keep this list short to avoid loose recommendations.
const BASIC_STAPLES = new Set([
  "water",
  "salt",
  "pepper",
  "black pepper",
  "ground black pepper",
  "cooking oil",
  "vegetable oil",
]);

const normalize = (value) =>
  String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9 ]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();

function phraseInside(longer, shorter) {
  if (!longer || !shorter) return false;
  const escaped = shorter.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`\\b${escaped}\\b`).test(longer);
}

/**
 * Match one recipe ingredient with one pantry item.
 * Word boundaries stop wrong matches such as "egg" matching "eggplant".
 */
function ingredientMatches(ingredient, pantryItem) {
  const ingredientKey = normalize(ingredient);
  const pantryKey = normalize(pantryItem);
  if (!ingredientKey || !pantryKey) return false;

  if (phraseInside(ingredientKey, pantryKey) || phraseInside(pantryKey, ingredientKey)) {
    return true;
  }

  // Allow a basic singular/plural difference: onion ↔ onions, egg ↔ eggs.
  const ingredientSingular = ingredientKey.length > 3 ? ingredientKey.replace(/s$/, "") : ingredientKey;
  const pantrySingular = pantryKey.length > 3 ? pantryKey.replace(/s$/, "") : pantryKey;
  return (
    phraseInside(ingredientSingular, pantrySingular) ||
    phraseInside(pantrySingular, ingredientSingular)
  );
}

function isBasicStaple(ingredient) {
  const key = normalize(ingredient);
  return [...BASIC_STAPLES].some(
    (staple) =>
      key === staple || key.startsWith(`${staple} `) || key.endsWith(` ${staple}`)
  );
}

/**
 * Rebuild the match information by checking the complete ingredient list.
 * Older code used only the first six ingredients, which could show a wrong
 * "Available Ingredients Only" badge.
 */
function applyPantryMatch(recipe, pantry = []) {
  const allIngredients = recipe.allIngredients || recipe.coreIngredients || [];
  const pantryItems = (pantry || []).map((item) => String(item).trim()).filter(Boolean);

  if (pantryItems.length === 0) {
    return {
      ...recipe,
      matched: [],
      missing: [],
      score: 0,
      tier: 3,
      availLines: [],
      missingLines: allIngredients,
      unusedPantry: [],
    };
  }

  const matchesAnyPantryItem = (ingredient) =>
    pantryItems.some((pantryItem) => ingredientMatches(ingredient, pantryItem));

  const matched = allIngredients.filter(matchesAnyPantryItem);
  const availLines = allIngredients.filter(
    (ingredient) => matchesAnyPantryItem(ingredient) || isBasicStaple(ingredient)
  );
  const missingLines = allIngredients.filter(
    (ingredient) => !availLines.includes(ingredient) && !isBasicStaple(ingredient)
  );
  const requiredIngredients = allIngredients.filter((ingredient) => !isBasicStaple(ingredient));
  const score = matched.length / (requiredIngredients.length || 1);
  const tier = missingLines.length === 0 ? 1 : missingLines.length <= 1 ? 2 : 3;
  const unusedPantry = pantryItems.filter(
    (pantryItem) => !allIngredients.some((ingredient) => ingredientMatches(ingredient, pantryItem))
  );

  return {
    ...recipe,
    matched,
    missing: missingLines,
    score,
    tier,
    availLines,
    missingLines,
    unusedPantry,
  };
}

function filterByName(recipes, nameQuery) {
  const query = normalize(nameQuery);
  if (!query) return recipes;
  return recipes.filter((recipe) => normalize(recipe.name).includes(query));
}

/**
 * Keep only recipes that use at least one pantry item, then sort the strongest
 * match first. This applies to both backend results and offline fallback data.
 */
function filterAndRankByPantry(recipes, pantry) {
  const pantryItems = (pantry || []).map((item) => String(item).trim()).filter(Boolean);
  if (pantryItems.length === 0) {
    return recipes.map((recipe) => applyPantryMatch(recipe, []));
  }

  return recipes
    .map((recipe) => applyPantryMatch(recipe, pantryItems))
    .filter((recipe) => recipe.matched.length > 0)
    .sort(
      (a, b) =>
        b.score - a.score ||
        a.missingLines.length - b.missingLines.length ||
        (a.timeMinutes || 999) - (b.timeMinutes || 999) ||
        a.name.localeCompare(b.name)
    )
    // Keep the interface responsive when the offline catalog has many matches.
    .slice(0, 100);
}

async function requestJson(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`Backend request failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Search and rank recipes using the backend first.
 * The source value lets App.jsx show a truthful connection badge.
 */
export async function searchRecipes(pantry, mealFilter, nameQuery) {
  try {
    const data = await requestJson("/api/recipes/search", {
      method: "POST",
      body: JSON.stringify({ pantry, mealFilter, nameQuery }),
    });

    const rawResults = Array.isArray(data) ? data : data.results || [];
    const namedResults = filterByName(rawResults, nameQuery);
    return {
      results: filterAndRankByPantry(namedResults, pantry),
      source: "backend",
    };
  } catch (error) {
    console.warn("Backend unavailable. Using the offline frontend catalog:", error);
    return {
      results: mockSearch(pantry, mealFilter, nameQuery),
      source: "frontend_fallback",
    };
  }
}

/**
 * Send a message and the previous conversation to the FastAPI backend.
 * History gives the chatbot memory for replies such as "Yes" or "Continue".
 */
export async function chatWithChef(userMessage, history = []) {
  const data = await requestJson("/api/chat", {
    method: "POST",
    body: JSON.stringify({
      user_message: userMessage,
      history,
    }),
  });

  return data.chef_reply || data.message || "Kitchen AI did not return a reply.";
}

/** Read the real Ollama and ChromaDB status from the backend. */
export async function getSystemHealth() {
  return requestJson("/health");
}

export async function getAllRecipes() {
  try {
    const data = await requestJson("/api/recipes/all");
    return data.results || [];
  } catch (error) {
    console.warn("Backend unavailable. Using local mock recipes:", error);
    return RECIPE_DATABASE;
  }
}

function mockSearch(pantry, mealFilter = "All", nameQuery = "") {
  const byMeal =
    mealFilter === "All"
      ? RECIPE_DATABASE
      : RECIPE_DATABASE.filter((recipe) => recipe.mealType === mealFilter);

  const byName = filterByName(byMeal, nameQuery);
  const results = filterAndRankByPantry(byName, pantry);

  if ((pantry || []).length > 0) return results;

  return results.sort(
    (a, b) => a.mealType.localeCompare(b.mealType) || a.name.localeCompare(b.name)
  );
}
