// =============================================================================
// LOCAL MOCK RECIPE DATABASE
// =============================================================================
// The UI normally reads recipes from the FastAPI backend at /api/recipes/search.
// This JSON copy is only a frontend fallback so the app can still render if the
// backend is not running yet.

import recipes from "./recipes.mock.json";

export const RECIPE_DATABASE = recipes;
