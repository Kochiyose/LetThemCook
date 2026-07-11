/**
 * Recipe service
 * --------------
 * Primary source: FastAPI backend using backend/data/LetThemCook_Core_Database.csv.
 * Fallback source: local recipes.mock.json, generated from the same CSV.
 */

import { RECIPE_DATABASE } from "../data/recipes.js";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const normalize = (value) =>
  String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9 ]+/g, " ")
    .trim();

/**
 * Builds the matched/missing/score/tier info the UI cards and modal rely on.
 * Unlike the backend, this checks the recipe's FULL ingredient list — not
 * just the first 6 "core" ones — so a searched ingredient (e.g. egg) shows
 * up as matched even if it's the 7th+ ingredient in the recipe. Recipes
 * that don't contain any searched ingredient are dropped entirely.
 */
function applyPantryMatch(recipe, pantryTerms) {
  const allIngredients = recipe.allIngredients || [];

  const hasMatch = (ingredient) => {
    const key = normalize(ingredient);
    return pantryTerms.some((term) => key.includes(term) || term.includes(key));
  };

  if (pantryTerms.length === 0) {
    const core = recipe.coreIngredients && recipe.coreIngredients.length
      ? recipe.coreIngredients
      : allIngredients.slice(0, 6);
    return { ...recipe, matched: [], missing: [], score: 0, tier: 3, coreIngredients: core, availLines: [], missingLines: allIngredients };
  }

  const matchedFull = allIngredients.filter(hasMatch);
  const others = allIngredients.filter((ingredient) => !matchedFull.includes(ingredient));
  // Show matched ingredients first, then fill up to 6 total with the rest,
  // so the "X/Y" badge and "Still need" list reflect reality.
  const displayCore = [...matchedFull, ...others].slice(0, Math.max(6, matchedFull.length));

  const matched = displayCore.filter(hasMatch);
  const missing = displayCore.filter((ingredient) => !hasMatch(ingredient));
  const score = matched.length / (displayCore.length || 1);
  const tier = missing.length === 0 ? 1 : missing.length <= 1 ? 2 : 3;

  const availLines = allIngredients.filter(hasMatch);
  const missingLines = allIngredients.filter((ingredient) => !hasMatch(ingredient));

  return {
    ...recipe,
    matched,
    missing,
    score,
    tier,
    coreIngredients: displayCore,
    availLines,
    missingLines,
  };
}


function filterByName(recipes, nameQuery) {
  const query = normalize(nameQuery);
  if (!query) return recipes;
  return recipes.filter((recipe) => normalize(recipe.name).includes(query));
}
/**
 * Strict ingredient filter + rescoring. Keeps only recipes that actually
 * contain at least one searched ingredient, then rebuilds the match info
 * for each so the UI badges are accurate. Runs entirely on the frontend
 * so it applies no matter where the recipe list came from (backend API or
 * the local mock fallback).
 */
function filterByPantry(recipes, pantry) {
  const pantryTerms = (pantry || []).map(normalize).filter(Boolean);
  if (pantryTerms.length === 0) return recipes;

  return recipes
    .filter((recipe) => {
      const haystack = (recipe.allIngredients || []).map(normalize).join(" ");
      return pantryTerms.some((term) => haystack.includes(term));
    })
    .map((recipe) => applyPantryMatch(recipe, pantryTerms))
    .sort(
      (a, b) =>
        b.score - a.score ||
        a.missing.length - b.missing.length ||
        (a.timeMinutes || 999) - (b.timeMinutes || 999) ||
        a.name.localeCompare(b.name)
    );
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
 * Search and rank recipes using the backend first, then local fallback.
 * @param {string[]} pantry
 * @param {"All" | "Breakfast" | "Lunch" | "Dinner"} mealFilter
 * @param {string} nameQuery
 * @returns {Promise<Array>}
 */
export async function searchRecipes(pantry, mealFilter, nameQuery) {
  try {
    const data = await requestJson("/api/recipes/search", {
      method: "POST",
      body: JSON.stringify({ pantry, mealFilter, nameQuery }),
    });

    const results = Array.isArray(data) ? data : data.results || [];
    const named = filterByName(results, nameQuery);
    return filterByPantry(named, pantry);
  } catch (error) {
    console.warn("Using local mock recipe database because backend is unavailable:", error);
    return mockSearch(pantry, mealFilter, nameQuery);
  }
}

/**
 * Send a message to Chef Llama through the FastAPI backend.
 * @param {string} userMessage
 * @returns {Promise<string>}
 */
export async function chatWithChef(userMessage) {
  const data = await requestJson("/api/chat", {
    method: "POST",
    body: JSON.stringify({ user_message: userMessage }),
  });

  return data.chef_reply || data.message || "Chef Llama did not return a reply.";
}

export async function getAllRecipes() {
  try {
    const data = await requestJson("/api/recipes/all");
    return data.results || [];
  } catch (error) {
    console.warn("Using local mock recipes because backend is unavailable:", error);
    return RECIPE_DATABASE;
  }
}

function mockSearch(pantry, mealFilter = "All", nameQuery = "") {
  const byMeal =
    mealFilter === "All"
      ? RECIPE_DATABASE
      : RECIPE_DATABASE.filter((recipe) => recipe.mealType === mealFilter);

  const query = normalize(nameQuery);
  const byName = query
    ? byMeal.filter((recipe) => normalize(recipe.name).includes(query))
    : byMeal;

  const pantryTerms = pantry.map(normalize).filter(Boolean);

  if (pantryTerms.length > 0) {
    return filterByPantry(byName, pantry);
  }

  const results = byName.map((recipe) => applyPantryMatch(recipe, []));
  return results.sort((a, b) => a.mealType.localeCompare(b.mealType) || a.name.localeCompare(b.name));
}