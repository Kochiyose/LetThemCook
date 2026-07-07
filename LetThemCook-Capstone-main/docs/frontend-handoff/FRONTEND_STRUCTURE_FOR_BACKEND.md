# Frontend Structure Guide for Backend Developers

> Written for backend developers. No frontend experience needed. This document explains what every file does and where to make changes.

## Table of Contents
1. [The Big Picture](#the-big-picture)
2. [File-by-File Breakdown](#file-by-file-breakdown)
3. [How Data Flows](#how-data-flows)
4. [How to Connect Your API](#how-to-connect-your-api)
5. [Common Tasks](#common-tasks)

---

## The Big Picture

Think of this app like a restaurant:

- **App.jsx** = The kitchen itself (handles all the cooking logic)
- **recipes.js** = The recipe book (contains all recipe data)
- **recipeService.js** = The order processing system (receives ingredients, returns matched recipes)
- **chat.config.js** = The greeting script (what the AI says)
- **ui.config.js** = The menu board (all visible text and labels)

**Users interact with the UI → React components render → Services fetch data → Display results**

---

## File-by-File Breakdown

### Entry Point: `src/main.jsx`
```javascript
import React from "react";
import App from "./app/App.jsx";
import "./styles/index.css";

// This is where React takes over the browser
createRoot(document.getElementById("root")).render(<App />);
```

**What it does:** Starts the entire app. You don't need to edit this.

---

### Main Component: `src/app/App.jsx` (~1,000 lines)
This is the nerve center of the app.

**Structure inside App.jsx:**
```
App.jsx
├── State (useState) - Data that changes when user interacts
│   ├── ingredients - List of what user has in pantry
│   ├── recipes - List of recipes to display
│   ├── selectedMealType - Current filter (All/Breakfast/Lunch/Dinner)
│   └── messages - Chat history
│
├── Helper Components (Mini-UIs)
│   ├── MealBadge - Shows meal type with colors
│   ├── RecipeCard - Individual recipe display
│   ├── RecipeModal - Popup showing full recipe details
│   └── ChatMessage - One chat message in the sidebar
│
└── Render (JSX) - What gets displayed on screen
    ├── Left Panel: Recipe browser
    │   ├── Header with app title
    │   ├── Ingredient input section
    │   ├── Filter buttons
    │   ├── Recipe grid
    │   └── Empty state (if no recipes found)
    │
    └── Right Panel: AI Chat
        ├── Welcome message
        ├── Chat history
        ├── Quick prompts
        └── Chat input
```

**Key Functions in App.jsx:**

| Function | What It Does | When It's Called |
|----------|-------------|-----------------|
| `handleAddIngredient()` | User enters ingredient → add to list | Input form submitted |
| `handleRemoveIngredient()` | User clicks X on ingredient → remove it | X button clicked |
| `handleMealTypeChange()` | User clicks filter button → update display | Filter button clicked |
| `handleSearchRecipes()` | Search + filter + sort recipes | Ingredient added/removed |
| `handleRecipeSelect()` | User clicks recipe → show full details | Recipe card clicked |
| `handleSendMessage()` | User sends chat message → get AI response | Chat form submitted |

---

### Configuration: `src/app/config/`

These files contain **ONLY TEXT** — no code logic. Edit these to change what users see.

#### `chat.config.js`
```javascript
export const WELCOME_MESSAGE = "Hi! I'm your cooking assistant..."
export const AI_FALLBACK_REPLIES = [
  "Reply 1...",
  "Reply 2...",
  "Reply 3..."
]
export const QUICK_PROMPTS = [
  "What can I make with eggs?",
  "How do I store herbs?"
]
```

**Who edits this:** Backend team changes AI responses when you connect real Ollama/API

**What to change:** 
- Replace `AI_FALLBACK_REPLIES` with real API responses
- Keep `WELCOME_MESSAGE` and `QUICK_PROMPTS` the same (or customize)

#### `ui.config.js`
```javascript
export const APP_IDENTITY = {
  name: "LetThemCook",
  tagline: "AI-Powered Recipe Finder"
}

export const MEAL_FILTERS = ["All", "Breakfast", "Lunch", "Dinner"]

export const INGREDIENT_INPUT = {
  label: "🛒 Enter Ingredients You Have at Home",
  placeholder: "e.g. eggs, butter, rice",
  addButton: "Add"
}
```

**Who edits this:** Anyone changing labels, button text, or messages

**What to change:** Any string value between quotes `" "`

---

### Data: `src/app/data/recipes.js`

This is the **recipe database**. It's a simple JavaScript array of objects.

```javascript
export const RECIPE_DATABASE = [
  {
    id: 1,
    name: "Scrambled Eggs",
    mealType: "Breakfast",
    coreIngredients: ["eggs", "butter", "salt", "pepper"],
    instructions: "1. Heat butter...\n2. Add eggs...",
    cookTime: 5,
    servings: 2
  },
  {
    id: 2,
    name: "Pasta Carbonara",
    mealType: "Lunch",
    coreIngredients: ["pasta", "eggs", "bacon", "parmesan"],
    instructions: "1. Boil pasta...\n2. Cook bacon...",
    cookTime: 20,
    servings: 4
  }
  // ... more recipes
];
```

**Key Fields Explained:**

| Field | Type | Example | Used For |
|-------|------|---------|----------|
| `id` | number | `1` | Unique identifier |
| `name` | string | `"Scrambled Eggs"` | Recipe title |
| `mealType` | string | `"Breakfast"` | Filter buttons |
| `coreIngredients` | array | `["eggs", "butter"]` | Matching algorithm |
| `instructions` | string | `"1. Heat...\n2. Add..."` | Recipe popup |
| `cookTime` | number | `5` | Display as "5 min" |
| `servings` | number | `2` | Display as "2 servings" |

**To add a recipe:** Copy an existing one, change the values.

**IMPORTANT:** `mealType` must be **exactly** one of:
- `"Breakfast"`
- `"Lunch"`
- `"Dinner"`

(Capital first letter!)

---

### Business Logic: `src/app/services/recipeService.js`

This is where **recipe matching happens**. It receives ingredients and returns ranked recipes.

```javascript
/**
 * Takes user's pantry and returns matching recipes, ranked by relevance
 * 
 * Input:  { ingredients: ["eggs", "butter"], mealType: "Breakfast", searchTerm: "" }
 * Output: [
 *   { ...recipe, score: 0.9, tier: 1, matched: ["eggs", "butter"] },
 *   { ...recipe, score: 0.5, tier: 3, matched: ["eggs"] },
 *   ...
 * ]
 */
export async function searchRecipes(ingredients, mealType, searchTerm) {
  // Current: Mock implementation (browser-side)
  // TODO: Replace with real API call to your FastAPI/Express backend
}
```

**The Mock Algorithm (current):**
1. For each recipe, count how many core ingredients user has
2. Calculate score = matched / total (0 to 1)
3. Assign tier (1 = perfect, 2 = missing 1, 3 = missing 2+)
4. Filter by mealType
5. Filter by search term
6. Sort by tier, then by score
7. Return sorted list

**How to Connect Your API:**

Replace this:
```javascript
// CURRENT (mock)
return _mockSearch(ingredients, mealType, searchTerm);
```

With this:
```javascript
// YOUR API CALL
const response = await fetch('/api/recipes/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    ingredients: ingredients,
    mealType: mealType,
    searchTerm: searchTerm
  })
});
return await response.json();
```

**Your API should return:**
```json
[
  {
    "id": 1,
    "name": "Scrambled Eggs",
    "mealType": "Breakfast",
    "coreIngredients": ["eggs", "butter"],
    "instructions": "...",
    "cookTime": 5,
    "servings": 2,
    "score": 0.9,
    "tier": 1,
    "matched": ["eggs", "butter"],
    "missing": []
  }
]
```

---

### Styling: `src/styles/index.css`

This is where Tailwind CSS is configured. Uses design tokens.

```css
@import 'tailwindcss';

@theme inline {
  --color-primary: #22c55e;
  --color-secondary: #f59e0b;
  /* ... more colors ... */
}
```

**To change colors:** Edit hex codes here, not in components.

---

## How Data Flows

Here's the complete journey of one user action:

```
User types "eggs" and clicks "Add"
         ↓
     App.jsx
  handleAddIngredient()
         ↓
 ingredients state updated
  ["eggs"]
         ↓
   handleSearchRecipes()
   triggered automatically
         ↓
  recipeService.js
  searchRecipes(["eggs"], "All", "")
         ↓
  Returns ranked recipes:
  [
    { id: 1, name: "Scrambled Eggs", score: 1.0, ... },
    { id: 5, name: "Omelette", score: 1.0, ... },
    { id: 8, name: "Pasta Carbonara", score: 0.5, ... }
  ]
         ↓
  recipes state updated
         ↓
  React re-renders <RecipeCard /> for each recipe
         ↓
  User sees updated recipe grid
```

---

## How to Connect Your API

### Step 1: Backend Ready?
- [ ] You have a FastAPI or Express server
- [ ] It has an endpoint like `/api/recipes/search`
- [ ] It accepts POST with `{ ingredients, mealType, searchTerm }`
- [ ] It returns array of recipes with `score` and `tier`

### Step 2: Update Frontend

Edit `src/app/services/recipeService.js`:

```javascript
export async function searchRecipes(ingredients, mealType, searchTerm) {
  try {
    const response = await fetch('http://your-backend.com/api/recipes/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ingredients: ingredients,
        mealType: mealType,
        searchTerm: searchTerm
      })
    });
    
    if (!response.ok) throw new Error('Search failed');
    return await response.json();
  } catch (error) {
    console.error('Recipe search error:', error);
    return []; // Return empty if API fails
  }
}
```

### Step 3: Connect AI Chat

Edit `src/app/services/recipeService.js`, add new function:

```javascript
export async function getAIResponse(messages) {
  try {
    const response = await fetch('http://your-backend.com/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: messages })
    });
    
    const data = await response.json();
    return data.reply;
  } catch (error) {
    console.error('AI error:', error);
    return "Sorry, I couldn't process that.";
  }
}
```

Then in `src/app/App.jsx`, find `handleSendMessage()`:

```javascript
async function handleSendMessage(e) {
  e.preventDefault();
  
  const userMessage = input.trim();
  setMessages(prev => [...prev, { id: Date.now(), role: "user", content: userMessage }]);
  setInput("");
  
  // Call your AI API instead of random replies
  const aiResponse = await getAIResponse(messages);
  
  setMessages(prev => [...prev, { 
    id: Date.now() + 1, 
    role: "assistant", 
    content: aiResponse 
  }]);
}
```

---

## Common Tasks

### Task: Add a New Recipe
**File:** `src/app/data/recipes.js`

```javascript
export const RECIPE_DATABASE = [
  // ... existing recipes ...
  {
    id: 17, // Must be unique!
    name: "My New Recipe",
    mealType: "Lunch", // Must be: Breakfast, Lunch, or Dinner
    coreIngredients: ["ingredient1", "ingredient2"],
    instructions: "Step 1.\nStep 2.\nStep 3.",
    cookTime: 25,
    servings: 4
  }
];
```

### Task: Change App Title
**File:** `index.html`
```html
<title>My Recipe App</title>
```

### Task: Change AI Personality
**File:** `src/app/config/chat.config.js`
```javascript
export const AI_FALLBACK_REPLIES = [
  "Your new response 1",
  "Your new response 2",
  // ...
];
```

### Task: Change Button Labels
**File:** `src/app/config/ui.config.js`
```javascript
export const INGREDIENT_INPUT = {
  label: "Enter ingredients",
  addButton: "Add Ingredient",
  // ...
};
```

### Task: Add Logging/Debugging
**In any component:**
```javascript
console.log("[v0] ingredients:", ingredients);
console.log("[v0] selectedMealType:", selectedMealType);
console.log("[v0] recipes returned:", recipes);
```

---

## Project Statistics

| Metric | Value |
|--------|-------|
| Total Lines | ~1,500 |
| Main Component | 1,000 lines (App.jsx) |
| Recipes | 16 (easily expandable) |
| Configuration Lines | 150 |
| Service Functions | 3 |
| UI Components (inline) | 8 |
| Styling | Tailwind CSS v4 |

---

## Tech Stack Reference

- **React 18** - UI library (component-based)
- **Vite 6** - Build tool (dev server & bundler)
- **Tailwind CSS 4** - Styling (utility classes)
- **Lucide React** - Icons (50+ available)
- **Framer Motion** - Animations (smooth transitions)
- **Radix UI** - Accessible dialogs/popovers

All imports are at the top of each file. No external packages beyond these.

---

## Key Principles

1. **Config files have NO code** — only text strings
2. **One service file for all API calls** — recipeService.js
3. **One big App component** — all state and logic live here
4. **Utility functions outside App** — MealBadge, RecipeCard, etc.
5. **Data flows down, events flow up** — React pattern
6. **Mock implementation by default** — ready for real API swap

---

## FAQ for Backend Developers

**Q: Where do I add my API endpoint?**
A: `src/app/services/recipeService.js` — replace the mock functions.

**Q: How do I handle errors from the API?**
A: Use try/catch blocks in recipeService.js. Return empty array or default value on error.

**Q: Can I add new fields to recipes?**
A: Yes! Add them to the recipe objects in `recipes.js`, then use them in `App.jsx`.

**Q: How do I test the UI while building the backend?**
A: The mock data is already there. Your app works offline. When you're ready, swap the API calls.

**Q: Where's the database code?**
A: Not here — that's on your backend. This is just the frontend. Your backend talks to the database.

**Q: What if I need to add a new component?**
A: Define it inside `App.jsx` (like MealBadge), or create a new file in `src/app/components/`.

**Q: How do I deploy this?**
A: Run `pnpm build`, then deploy the `dist/` folder.

---

## Summary

**For Backend Developers:**
- Everything you need is in `recipeService.js`
- Connect your API endpoints there
- The mock data works offline
- All text is in config files
- React handles the UI automatically

**You don't need to understand React deeply** — just:
1. Find what needs changing
2. Find where to change it
3. Make the change
4. Save and refresh

The UI already looks perfect. You just need to plug in your backend! 🎉
