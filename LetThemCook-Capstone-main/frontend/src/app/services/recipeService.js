/**
 * Recipe service
 * --------------
 * Primary source: FastAPI + ChromaDB (100% Local Edge AI)
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

// Basic household staples
const BASIC_STAPLES = new Set([
  "water",
  "salt",
  "pepper",
  "black pepper",
  "ground black pepper",
  "cooking oil",
  "vegetable oil",
]);

/**
 * Wrapper for fetching JSON from the FastAPI backend.
 */
async function requestJson(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API Error ${response.status}: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Parse the strict JSON structure returned by Llama 3.2.
 */
export async function getAiRecipe(ingredientsArray) {
  try {
    const ingredientsString = ingredientsArray.join(", ");
    const data = await requestJson("/api/generate-recipe", {
      method: "POST",
      body: JSON.stringify({
        user_ingredients: ingredientsString,
        max_time_minutes: 120,
      }),
    });

    let payload = data.chef_reply;
    if (typeof payload === "string") {
      payload = JSON.parse(payload);
    }

    return {
      ...payload,
      source: "backend",
    };
  } catch (error) {
    console.error("AI Generation Error:", error);
    return {
      dish_name: "System Offline / Error",
      used_ingredients: [],
      missing_ingredients: [],
      assumed_staples: [],
      execution_steps: ["The AI backend is currently unreachable or timed out. Please ensure Ollama and FastAPI are running."],
      source: "error",
    };
  }
}

/**
 * Send a message and the previous conversation to the FastAPI backend.
 */
export async function chatWithChef(userMessage, ingredients = [], history = []) {
  try {
    const data = await requestJson("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        user_message: userMessage,
        ingredients: ingredients,
        history,
      }),
    });
    return data.chef_reply || data.message || "Kitchen AI did not return a reply.";
  } catch (error) {
    console.error("Chat Error:", error);
    return "The AI backend is currently unreachable.";
  }
}

export async function getSystemHealth() {
  try {
    return await requestJson("/health");
  } catch (error) {
    return { status: "offline" };
  }
}

export async function getAllRecipes() {
  try {
    const data = await requestJson("/api/recipes/all");
    return data.results || [];
  } catch (error) {
    console.warn("Backend unavailable. Returning empty catalog.", error);
    return [];
  }
}

export async function searchRecipes(pantry, mealFilter = "All", nameQuery = "") {
  const userIngredients = Array.isArray(pantry) ? pantry.join(", ") : pantry;

  try {
    const data = await requestJson("/api/recipes/search", {
      method: "POST",
      body: JSON.stringify({
        user_ingredients: userIngredients,
        max_time_minutes: 120,
      }),
    });

    return {
      results: data.results || [],
      source: "backend",
    };
  } catch (error) {
    console.error("Backend API unavailable. Could not fetch recipes.", error);
    return { results: [], source: "error" };
  }
}