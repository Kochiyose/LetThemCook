# 🍳 LetThemCook - Beginner's Guide for Backend Developers

Welcome! This guide is designed to help you understand and edit the LetThemCook application. **Don't worry if you're new to React or JavaScript** — we've kept everything simple and well-documented.

---

## 📁 Project Structure

```
src/
├── app/
│   ├── App.jsx                    ← THE MAIN COMPONENT (UI shell)
│   ├── config/
│   │   ├── chat.config.js         ← 💬 AI chat messages & prompts (EASY TO EDIT!)
│   │   └── ui.config.js           ← 🎨 All button labels & text (EASY TO EDIT!)
│   ├── data/
│   │   └── recipes.js             ← 🍽️ Recipe database (EASY TO ADD RECIPES!)
│   ├── services/
│   │   └── recipeService.js       ← 🔍 Recipe search logic
│   └── components/
│       └── ui/                    ← Reusable UI components
├── styles/
│   └── index.css                  ← Global styles
└── main.jsx                       ← Entry point

index.html                         ← Root HTML file
vite.config.js                     ← Build configuration
package.json                       ← Dependencies
```

---

## 🚀 Getting Started

### What Language Is This?
This is **JavaScript** (not TypeScript). All files now end in `.js` or `.jsx`:
- `.js` = Regular JavaScript files
- `.jsx` = JavaScript files with React code inside

### Running the App
```bash
npm install    # Install dependencies
npm run dev    # Start the development server
```

The app will open in your browser automatically. As you edit files, the browser will refresh automatically!

---

## 📝 Making Your First Changes

### 1. Change App Name & Tagline (EASIEST!)
**File:** `src/app/config/ui.config.js`

Look for this near the top:
```javascript
export const APP_IDENTITY = {
  name: "LetThemCook",                    // ← Change this
  tagline: "AI-Powered Recipe Finder",    // ← Or this
  aiStatus: "Llama 3.2 · Local",          // ← Or this
};
```

Save the file, and the browser will update instantly! 

✅ **No TypeScript knowledge required** — it's just plain text inside an object.

---

### 2. Change Button Labels & Text
**File:** `src/app/config/ui.config.js`

Find the section you want to change. For example, to change the "Add" button:
```javascript
export const INGREDIENT_INPUT = {
  label: "🛒 Enter Ingredients You Have at Home",
  hint: "Add one at a time or separate multiple with commas…",
  placeholder: "e.g. eggs, butter, rice…",
  addButton: "Add",    // ← Change "Add" to something else
  clearAll: "Clear all",
  // ... more options below
};
```

**Rule:** Don't change the variable names (like `addButton`), only the text inside the quotes.

---

### 3. Change AI Chat Messages
**File:** `src/app/config/chat.config.js`

This file controls everything the AI says. The welcome message is at the top:
```javascript
export const WELCOME_MESSAGE =
  "Hi there! 👨‍🍳 I'm your local AI cooking assistant…";
```

And the fallback replies (shown while real AI is disconnected):
```javascript
export const AI_FALLBACK_REPLIES = [
  "Great choice! With those ingredients…",  // Reply 1
  "Good question! If you're out of butter…", // Reply 2
  "That's the smart approach!…",            // Reply 3
  // Add more here!
];
```

**To add a new AI reply:** Just add a new line:
```javascript
export const AI_FALLBACK_REPLIES = [
  // ... existing replies ...
  "Your new reply here!",  // ← New line
];
```

**Quick prompts** (the buttons above the chat input):
```javascript
export const QUICK_PROMPTS = [
  "What can I make with eggs and butter?",
  "How do I store leftover herbs?",
  "Can I substitute oil for butter?",
  // Add more questions here!
];
```

---

### 4. Add a New Recipe (FUN PART!)
**File:** `src/app/data/recipes.js`

Look for the `RECIPE_DATABASE` array. Each recipe looks like this:
```javascript
{
  id: 1,                                    // Unique number (just increment)
  name: "Scrambled Eggs",                   // Recipe name
  mealType: "Breakfast",                    // "Breakfast" | "Lunch" | "Dinner"
  prepTime: "3 min",                        // How long to prep
  cookTime: "5 min",                        // How long to cook
  totalTime: "8 min",                       // Total time
  cookingMethod: "Pan-fry",                 // Cooking technique
  coreIngredients: ["eggs", "butter"],      // Key ingredients for matching
  allIngredients: [                         // Complete ingredient list
    "3 large eggs",
    "1 tbsp butter",
    "2 tbsp milk",
    "Salt and black pepper",
    "Fresh chives to garnish",
  ],
  instructions: [                           // Step-by-step cooking
    "Crack eggs into a bowl…",
    "Melt butter in a non-stick pan…",
    "Pour in eggs…",
    // etc
  ],
},
```

**To add your own recipe:**

1. Copy the above structure
2. Change `id` to the next number (e.g., if last recipe is 16, use 17)
3. Fill in your recipe details
4. Paste it into the array before the closing bracket `]`

**Important:** The `coreIngredients` array is used to match recipes with user's pantry. Include 2–4 defining ingredients, but exclude common staples like salt, pepper, oil, garlic, onion.

---

## 🎨 Understanding React Components

Don't worry — we've hidden all the complex React stuff. But here are the basics:

### What's a Component?
A component is just a function that returns HTML-like code (called JSX). Think of it as a reusable building block.

Example (from `App.jsx`):
```javascript
function MealBadge({ type }) {
  // This is a "prop" — data passed into the function
  const styles = {
    Breakfast: "bg-amber-50 text-amber-700…",
    Lunch: "bg-sky-50…",
    Dinner: "bg-violet-50…",
  };
  
  // This is JSX — looks like HTML but it's JavaScript!
  return (
    <span className={`inline-flex … ${styles[type]}`}>
      {type}
    </span>
  );
}
```

**Key point:** JSX looks like HTML, but it's actually JavaScript. That weird `{type}` syntax is how you insert JavaScript values into HTML.

### State (Remembering Things)
React uses `useState` to remember data:
```javascript
const [pantry, setPantry] = useState([]);
// pantry = current ingredients list
// setPantry = function to update the list
```

You don't need to understand this deeply — it's all in `App.jsx` already!

---

## 🔧 Connecting Your Real Backend

### Current State
Right now, when you add ingredients, the app uses a **mock search** that runs in your browser. The fallback AI replies are hardcoded.

### When You Have a Backend API
You'll edit these two files:

**1. For real recipe search, edit:** `src/app/services/recipeService.js`

Look for the `searchRecipes()` function. Currently:
```javascript
export function searchRecipes(pantry, mealFilter, nameQuery) {
  // ... filter by meal type and name...
  return _mockSearch(pantry, byName);  // ← This uses local browser data
}
```

Replace it with:
```javascript
export async function searchRecipes(pantry, mealFilter, nameQuery) {
  const response = await fetch('https://your-backend.com/api/recipes/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pantry, mealFilter, nameQuery }),
  });
  return await response.json();
}
```

**2. For real AI chat, edit:** `src/app/config/chat.config.js`

Delete (or ignore) the `AI_FALLBACK_REPLIES` array once your real Ollama/LLM endpoint is connected. Update `App.jsx` to call your API instead of showing fallback messages.

---

## 💡 Tips for Editing

### Comment Your Changes
If you add recipes or change config, leave a comment:
```javascript
// Added by John on June 21 - New vegetarian section
{
  id: 17,
  name: "Tofu Stir-Fry",
  // ...
},
```

### Save Early & Often
The dev server has hot-reload — your changes appear in the browser instantly!

### Don't Rename Variables
Only change the text inside quotes. Don't do this:
```javascript
// ❌ WRONG
addButt: "Add",  // Renamed the variable!

// ✅ RIGHT
addButton: "Add",  // Only changed the text
```

---

## 🐛 Common Issues & How to Fix Them

### "Cannot find module" Error
**Cause:** Typo in import path or file name  
**Fix:** Check the file path is correct and uses `.js` or `.jsx` extension

### Styles aren't applied
**Cause:** Typo in Tailwind class name  
**Fix:** Make sure it matches a real Tailwind class (e.g., `bg-primary`, `text-sm`)

### Changes not showing
**Cause:** Browser cache or Vite not reloading  
**Fix:** 
1. Press `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac) to hard-refresh
2. Check the terminal for error messages

### Recipe doesn't appear in search
**Cause:** Typo in `mealType` — must exactly match ("Breakfast" not "breakfast")  
**Fix:** Make sure mealType is exactly "Breakfast", "Lunch", or "Dinner"

---

## 📚 File-by-File Reference

| File | Purpose | Edit For |
|------|---------|----------|
| `src/app/config/ui.config.js` | All UI text & labels | Button text, section headers, placeholders |
| `src/app/config/chat.config.js` | AI messages & prompts | Welcome message, AI replies, quick buttons |
| `src/app/data/recipes.js` | Recipe database | Add/edit recipes, ingredients, instructions |
| `src/app/services/recipeService.js` | Search logic | Connect to real backend API (advanced) |
| `src/app/App.jsx` | Main UI component | Layout, structure, state management (advanced) |
| `vite.config.js` | Build config | Rarely needed |

---

## 🎓 Next Steps

1. **Make a small change** (e.g., change app name) → See it work instantly!
2. **Add a new recipe** → Try editing the recipes.js file
3. **Change chat messages** → Personalize the AI responses
4. **Connect your backend** → Once your API is ready, update `recipeService.js`

---

## ❓ Questions?

**For JavaScript/React basics:**
- [MDN JavaScript Basics](https://developer.mozilla.org/en-US/docs/Learn/JavaScript)
- [React Hello World](https://react.dev/learn)

**For Tailwind CSS (styling):**
- [Tailwind CSS Docs](https://tailwindcss.com/docs)

**For this specific project:**
- Check the comments in each file — we've documented everything!
- Look at the structure of existing recipes when adding new ones

---

## 🎉 You've Got This!

The project is built for beginners. If you can edit text in a document, you can edit this app. Start small, save often, and enjoy!

Happy cooking! 🍳
