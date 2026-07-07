# Quick Start - LetThemCook (JavaScript Edition)

## For Backend Developers - Start Here! 👨‍💻

Welcome! This app is now 100% JavaScript (no TypeScript). Everything you need to know to modify and understand the code is below.

---

## 1️⃣ Get Started in 2 Minutes

```bash
# Install dependencies
pnpm install

# Start the development server
pnpm dev

# Open browser to http://localhost:5173
```

That's it! The app is now running.

---

## 2️⃣ Project Structure (Easy Version)

```
src/
├── main.jsx                    ← App starts here
├── app/
│   ├── App.jsx                ← Main component (all logic is here!)
│   ├── config/
│   │   ├── chat.config.js      ← Change AI responses
│   │   └── ui.config.js        ← Change colors/styling
│   ├── data/
│   │   └── recipes.js          ← Add recipes here
│   └── services/
│       └── recipeService.js    ← Recipe matching logic
```

**Tip:** 90% of what you'll edit is in `App.jsx`

---

## 3️⃣ What Does This App Do?

**LetThemCook** is an AI-powered recipe finder:
1. User enters ingredients they have
2. App finds matching recipes
3. AI assistant gives cooking help
4. User can filter by meal type (breakfast, lunch, dinner)

---

## 4️⃣ Common Things You'll Want to Change

### Add a New Recipe

**File:** `src/app/data/recipes.js`

Find the `recipes` array and add:
```javascript
{
  id: 17,
  name: "Pasta Primavera",
  type: "DINNER",  // BREAKFAST, LUNCH, or DINNER
  ingredients: ["pasta", "vegetables", "oil", "garlic"],
  instructions: "1. Boil pasta. 2. Sauté vegetables. 3. Mix together.",
  cookTime: 20,
  servings: 4
}
```

Save and refresh your browser - new recipe appears immediately!

---

### Change App Title

**File:** `index.html` (line 7-8)

Change:
```html
<title>LetThemCook</title>
```

To whatever you want:
```html
<title>My Cool Recipe App</title>
```

---

### Change Colors

**File:** `src/app/config/ui.config.js`

Look for `colors` section and edit:
```javascript
colors: {
  primary: '#22c55e',      // Green for buttons
  secondary: '#f59e0b',    // Orange for accents
  background: '#ffffff'    // White background
}
```

---

### Change AI Personality

**File:** `src/app/config/chat.config.js`

Edit the `systemPrompt`:
```javascript
const systemPrompt = `You are a friendly cooking expert...`;
```

Change this text to make the AI respond differently!

---

## 5️⃣ Understanding the Main App (App.jsx)

This is where everything happens. Here's what's in there:

### State (Variables That Change)

```javascript
const [ingredients, setIngredients] = useState([]);      // Ingredients user added
const [recipes, setRecipes] = useState([]);              // Filtered recipes
const [selectedMealType, setSelectedMealType] = useState("ALL"); // Filter type
const [messages, setMessages] = useState([]);            // Chat messages
```

### Main Functions

| Function | What It Does |
|----------|-------------|
| `handleAddIngredient()` | User clicks "ADD" to add ingredient |
| `handleMealTypeChange()` | User clicks meal type filter |
| `handleRecipeSelect()` | User clicks a recipe to see details |
| `handleSendMessage()` | User sends chat message to AI |

---

## 6️⃣ How Recipe Matching Works

**File:** `src/app/services/recipeService.js`

Simple explanation:
1. For each recipe, count how many ingredients match
2. Calculate a score (0-100%)
3. Sort recipes by score (highest first)
4. Show recipes in that order

**Example:**
- Recipe needs: eggs, butter, bread
- User has: eggs, butter, milk
- Match: 2 out of 3 = 66% score

---

## 7️⃣ How to Debug Issues

### 1. Open Developer Tools
Press `F12` in your browser

### 2. Go to Console Tab
You'll see errors here if something breaks

### 3. Add Debug Logs
In `App.jsx`, add this to any function:
```javascript
console.log("Debug info here:", someVariable);
```

Then check the console to see the output.

### 4. Check Network Tab
If AI isn't responding, see if API calls are working:
- Look in Network tab
- Look for failed requests
- Check if Llama service is running

---

## 8️⃣ Important Files Quick Reference

| File | Purpose | Edit When... |
|------|---------|--------------|
| `App.jsx` | Main component | Need to change app logic |
| `recipes.js` | Recipe data | Want to add/remove recipes |
| `chat.config.js` | AI prompts | Want AI to behave differently |
| `ui.config.js` | Colors/styling | Want to change look |
| `recipeService.js` | Recipe logic | Need to change scoring |
| `index.html` | HTML page | Changing title/favicon |

---

## 9️⃣ Key JavaScript Concepts Used

These are all the "advanced" things in this codebase - but they're simple:

**useState** - Remember data between renders
```javascript
const [count, setCount] = useState(0);
setCount(count + 1);  // Updates count
```

**map()** - Loop through array and transform it
```javascript
recipes.map(recipe => <RecipeCard recipe={recipe} />)
```

**filter()** - Keep only items that match
```javascript
recipes.filter(r => r.type === "BREAKFAST")
```

**onClick** - Run function when user clicks
```javascript
<button onClick={() => handleClick()}>Click me</button>
```

---

## 🔟 Real Example: Add a Recipe Step-by-Step

1. Open `src/app/data/recipes.js`
2. Scroll to the bottom of the `recipes` array
3. Copy the last recipe object
4. Paste it before the closing bracket
5. Change the values:
   ```javascript
   {
     id: 17,
     name: "Your Recipe",
     type: "LUNCH",
     ingredients: ["ingredient1", "ingredient2"],
     instructions: "Step 1... Step 2...",
     cookTime: 30,
     servings: 2
   }
   ```
6. Save file (Ctrl+S)
7. Browser auto-refreshes - new recipe appears!

---

## Troubleshooting

**Problem:** App shows blank screen
- Solution: Check browser console (F12) for red errors

**Problem:** New recipe doesn't appear
- Solution: Make sure `id` is unique and `type` is spelled correctly

**Problem:** AI doesn't respond
- Solution: Make sure Llama 3.2 local service is running

**Problem:** Can't find a file
- Solution: Use Ctrl+P in code editor to search

---

## Next Steps

1. ✅ Run `pnpm dev` and see it work
2. ✅ Add a recipe to `recipes.js`
3. ✅ Change a color in `ui.config.js`
4. ✅ Edit the AI prompt in `chat.config.js`
5. ✅ You now understand the whole app!

---

## Questions?

Each JavaScript file has comments explaining what it does. Look for `//` comments in the code - they explain everything!

Enjoy building! 🚀
