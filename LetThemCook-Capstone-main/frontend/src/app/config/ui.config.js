// =============================================================================
// This file controls all visible text, labels, placeholders, and messages
// shown in the recipe browser panel (the left side of the screen).
//
// HOW TO EDIT:
//   - Change any string value between the quotes " "
//   - Do NOT rename the exported variables — App.js imports them by name
//   - Save the file — the browser will hot-reload automatically
// =============================================================================


// The app name and tagline shown in the top-left header
export const APP_IDENTITY = {
  name: "LetThemCook",
  tagline: "AI-Powered Recipe Finder",
  // Fallback text only. App.jsx now shows the live status from FastAPI /health.
  aiStatus: "Checking local services",
};


// Filter buttons shown above the recipe grid
// RULES: "All" must be first, others must match recipe mealType (case-sensitive)
export const MEAL_FILTERS = ["All", "Breakfast", "Lunch", "Dinner"];


// Labels for the ingredient input section at the top
export const INGREDIENT_INPUT = {
  label: "🛒 Enter Ingredients You Have at Home",
  hint: "Add one at a time or separate multiple with commas — e.g. eggs, butter, rice",
  placeholder: "e.g. eggs, butter, rice — separate multiple with commas",
  addButton: "Add",
  clearAll: "Clear all",
  countSuffix: "ingredient",
  countSuffixPlural: "ingredients",
  scrollHint: "scroll to see all",
};


// The recipe-name search input
export const SEARCH_BAR = {
  placeholder: "Search recipe name…",
  mealLabel: "Meal:",
};


// Small status bar above the recipe grid showing how many recipes match
export const STATUS_BAR = {
  rankedPrefix: "Ranked by match:",
  perfect: "perfect",
  withAdditional: "with additional",
  recipesSuffix: "recipes shown",
};


// The "How it works" explainer card shown before ingredients are added
export const HOW_IT_WORKS = {
  title: "How it works",
  body: "Add ingredients you have at home and the AI will instantly rank every recipe by how well it matches your pantry — recipes you can cook right now appear first.",
};


// Badges shown on each recipe card
export const RECIPE_CARD_LABELS = {
  availableOnly: "Available Ingredients Only",
  withAdditional: "With Additional Ingredients",
  matchLabel: "Ingredient match",
};


// Labels inside the recipe detail popup (modal)
export const RECIPE_MODAL = {
  ingredientsHeading: "Ingredients",
  instructionsHeading: "Instructions",
  availableSubLabel: "Available Ingredients",
  additionalDivider: "Additional Ingredients",
  cookingMethodLabel: "Cooking Method",
  totalTimeLabel: "Total Time",
};


// Shown when no recipes match the current search/filter
export const EMPTY_STATE = {
  icon: "🍽️",
  title: "No recipes found",
  body: "Try a different filter or search term",
};


// Tab labels shown on mobile/tablet screens
export const MOBILE_TABS = {
  recipes: "Recipes",
  chat: "Chef Logro",
};
