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

    return Array.isArray(data) ? data : data.results || [];
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
  const results = byName.map((recipe) => rankRecipe(recipe, pantryTerms));

  if (pantryTerms.length > 0) {
    return results.sort(
      (a, b) =>
        b.score - a.score ||
        a.missing.length - b.missing.length ||
        (a.timeMinutes || 999) - (b.timeMinutes || 999) ||
        a.name.localeCompare(b.name)
    );
  }

  return results.sort((a, b) => a.mealType.localeCompare(b.mealType) || a.name.localeCompare(b.name));
}

function rankRecipe(recipe, pantryTerms) {
  const core = recipe.coreIngredients || [];

  const hasMatch = (ingredient) => {
    const key = normalize(ingredient);
    return pantryTerms.some((item) => key.includes(item) || item.includes(key));
  };

  const matched = pantryTerms.length > 0 ? core.filter(hasMatch) : [];
  const missing = pantryTerms.length > 0 ? core.filter((ingredient) => !hasMatch(ingredient)) : [];
  const score = pantryTerms.length > 0 ? matched.length / (core.length || 1) : 0;
  const tier = pantryTerms.length > 0 && missing.length === 0 ? 1 : pantryTerms.length > 0 && missing.length <= 1 ? 2 : 3;

  const availLines = (recipe.allIngredients || []).filter((line) =>
    matched.some((ingredient) => normalize(line).includes(normalize(ingredient)))
  );
  const missingLines = (recipe.allIngredients || []).filter((line) => !availLines.includes(line));

  return {
    ...recipe,
    matched,
    missing,
    score,
    tier,
    availLines,
    missingLines,
  };
}
