# JavaScript Migration Guide - LetThemCook

## Overview
Your TypeScript project has been successfully converted to pure JavaScript! All functionality remains the same, but now it's much easier for backend developers to understand and modify.

## What Changed

### File Extensions
- `*.ts` → `*.js` (TypeScript files to JavaScript)
- `*.tsx` → `*.jsx` (TypeScript React components to JavaScript)

### Configuration Files
- `vite.config.ts` → `vite.config.js`
- `index.html` script entry now points to `/src/main.jsx` instead of `/src/main.tsx`

### Key Files Converted

#### 1. **App.jsx** (Main Component)
```javascript
// Now uses plain JavaScript without type annotations
// All React hooks work exactly the same
// Comments explain each section for beginners
```

**What it does:**
- Manages recipes state and ingredient tracking
- Handles meal type filtering
- Integrates AI chat functionality
- Manages recipe modal display

**How to edit:**
- Search for function names to find what you need
- All state is managed with `useState` hooks
- Refer to inline comments for guidance

#### 2. **config/chat.config.js**
Contains system prompts for the AI assistant. Edit here to change:
- How the AI responds
- Cooking tips and guidance
- Recipe recommendation logic

#### 3. **config/ui.config.js**
Controls UI styling and colors:
- Background colors
- Text colors
- Button styles
- Component spacing

#### 4. **data/recipes.js**
All recipe data is stored here as a simple array of objects:
```javascript
{
  id: 1,
  name: "Recipe Name",
  type: "BREAKFAST", // or LUNCH, DINNER
  ingredients: ["ingredient1", "ingredient2"],
  instructions: "Step by step...",
  cookTime: 20,
  servings: 2
}
```

**To add a new recipe:**
1. Find `recipes.js`
2. Copy an existing recipe object
3. Change the `id`, `name`, `ingredients`, `instructions`
4. Save and reload

#### 5. **services/recipeService.js**
This file contains helper functions that:
- Calculate recipe matches based on available ingredients
- Filter recipes by meal type
- Search recipes by name

## Running the Project

### Start Development Server
```bash
pnpm dev
```
This will start the Vite server on `http://localhost:5173`

### Build for Production
```bash
pnpm build
```

### Preview Production Build
```bash
pnpm preview
```

## Understanding the Code Structure

### How Recipes Are Matched
1. User enters ingredients
2. App checks each recipe's required ingredients
3. Recipes are scored based on how many ingredients match
4. Results are sorted by score (highest match first)

**Location:** `src/app/services/recipeService.js` - `matchRecipes()` function

### How Filtering Works
1. User clicks a meal type button (BREAKFAST, LUNCH, DINNER)
2. App filters recipes to only show selected type
3. Search results are filtered too

**Location:** `src/app/App.jsx` - `handleMealTypeChange()` function

### How the AI Chat Works
1. Messages are sent to the local Llama 3.2 model
2. AI responds based on the system prompt
3. Chat history is maintained in the component state

**Location:** `src/app/App.jsx` - `handleSendMessage()` function

## Common Customizations

### Change App Title
Edit `index.html`:
```html
<title>Your New Title Here</title>
```

### Change Colors
Edit `src/app/config/ui.config.js`:
```javascript
colors: {
  primary: '#your-color-code',
  secondary: '#your-color-code'
}
```

### Add a New Recipe
Edit `src/app/data/recipes.js` and add to the `recipes` array:
```javascript
{
  id: 17,
  name: "Your Recipe Name",
  type: "BREAKFAST",
  ingredients: ["egg", "bread", "butter"],
  instructions: "1. Cook eggs... 2. Toast bread...",
  cookTime: 15,
  servings: 2
}
```

### Change AI Behavior
Edit `src/app/config/chat.config.js` and modify the `systemPrompt` to change how the AI responds.

## File Organization

```
src/
├── main.jsx                 # Entry point - starts the React app
├── index.css               # Global styles
├── app/
│   ├── App.jsx            # Main component with all logic
│   ├── config/
│   │   ├── chat.config.js  # AI system prompts
│   │   └── ui.config.js    # UI colors and styling
│   ├── data/
│   │   └── recipes.js      # All recipe data
│   └── services/
│       └── recipeService.js # Recipe matching logic
```

## No More TypeScript Needed!

You no longer need TypeScript knowledge:
- No type annotations (no `string`, `number`, etc.)
- No interfaces or types to define
- Just plain JavaScript functions and objects
- Comments explain what everything does

## Debugging Tips

### Open Browser Developer Tools
- Press `F12` or right-click → Inspect
- Go to Console tab to see any errors
- Use Network tab to check AI API calls

### Check Component State
- Add `console.log()` statements to see what values are stored
- Example: `console.log("Current ingredients:", ingredients)`

### Common Issues

**Problem:** Recipes not showing
- Solution: Check `data/recipes.js` to ensure recipes exist

**Problem:** AI not responding
- Solution: Make sure Llama 3.2 service is running locally

**Problem:** Ingredients not being added
- Solution: Check the `handleAddIngredient()` function in `App.jsx`

## Next Steps

1. **Customize recipes** - Add your own recipe collection
2. **Modify UI** - Update colors and styling in `ui.config.js`
3. **Enhance AI** - Create better prompts in `chat.config.js`
4. **Deploy** - Use Vercel or any host to deploy your app

## Questions?

Refer to the comments in each file - they explain:
- What each function does
- How state flows through components
- Where to make changes

Each file has beginner-friendly comments explaining the code!
