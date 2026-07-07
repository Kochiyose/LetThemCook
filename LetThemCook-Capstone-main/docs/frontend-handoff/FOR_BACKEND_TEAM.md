# For Backend Team: Frontend Overview

This is your quick-start guide to understand and modify the frontend code.

---

## Who This Is For

- Backend developers joining the project
- API developers building the backend
- System architects integrating frontend + backend
- Anyone who doesn't know React but needs to understand the code

---

## The 30-Second Summary

**What Frontend Does:**
1. User enters ingredients
2. Frontend sends them to backend API
3. Backend returns ranked recipes
4. Frontend displays them

**What You Need to Do:**
1. Build backend API that accepts ingredients
2. Connect it to `src/app/services/recipeService.js`
3. Your API returns recipes with scores
4. Frontend displays results automatically

**Tech Stack:**
- React.js (UI framework)
- Vite (build tool)
- Tailwind CSS (styling)
- Pure JavaScript (no TypeScript)

---

## File Organization (Simple)

```
src/
├── main.jsx                    ← Don't touch
├── app/
│   ├── App.jsx                 ← All UI + logic (1000 lines)
│   ├── config/
│   │   ├── chat.config.js      ← Edit: AI responses
│   │   └── ui.config.js        ← Edit: Button labels
│   ├── data/
│   │   └── recipes.js          ← Edit: Recipe data
│   └── services/
│       └── recipeService.js    ← EDIT: Connect API here ⭐
└── styles/
    └── index.css               ← Edit: Colors
```

**Bottom line:** Edit `recipeService.js`. Everything else is UI.

---

## How Frontend Works (From Backend Perspective)

### Current State (Mock)
```
User enters ingredients
       ↓
React state updates
       ↓
Mock function in recipeService.js runs
       ↓
Returns hardcoded recipes
       ↓
React displays them
```

### With Your Backend
```
User enters ingredients
       ↓
React state updates
       ↓
Calls YOUR API from recipeService.js
       ↓
Your API returns recipes with scores
       ↓
React displays them
```

**Only 1 file changes:** `src/app/services/recipeService.js`

---

## What the API Should Do

**Receives:**
```json
{
  "ingredients": ["eggs", "butter", "milk"],
  "mealType": "All",
  "searchTerm": ""
}
```

**Returns:**
```json
[
  {
    "id": 1,
    "name": "Scrambled Eggs",
    "mealType": "Breakfast",
    "coreIngredients": ["eggs", "butter"],
    "instructions": "1. Heat butter\n2. Add eggs",
    "cookTime": 5,
    "servings": 2,
    "score": 0.9,
    "tier": 1,
    "matched": ["eggs", "butter"],
    "missing": []
  }
]
```

**Key Fields:**
- `score`: 0.0 to 1.0 (how well ingredients match)
- `tier`: 1 (perfect), 2 (missing 1), 3 (missing 2+)
- `matched`: Ingredients user has
- `missing`: Ingredients user doesn't have

---

## Connecting Your API (Copy-Paste)

### Step 1: Open This File
```
src/app/services/recipeService.js
```

### Step 2: Find This Function
```javascript
export async function searchRecipes(ingredients, mealType, searchTerm) {
  return _mockSearch(ingredients, mealType, searchTerm);
}
```

### Step 3: Replace With This
```javascript
export async function searchRecipes(ingredients, mealType, searchTerm) {
  try {
    const response = await fetch('http://localhost:3000/api/recipes/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ingredients: ingredients,
        mealType: mealType,
        searchTerm: searchTerm
      })
    });
    
    if (!response.ok) throw new Error('API error');
    return await response.json();
    
  } catch (error) {
    console.error('Search failed:', error);
    return [];  // Return empty if API fails
  }
}
```

### Step 4: Change the URL
Replace `'http://localhost:3000/api/recipes/search'` with your backend URL.

### Step 5: Test
- Run `pnpm dev`
- Open http://localhost:5173
- Add an ingredient
- Check browser Network tab (F12)
- Should see request to your API

---

## Backend API Examples

### FastAPI (Python)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"])

@app.post("/api/recipes/search")
async def search(request: dict):
    ingredients = request["ingredients"]
    meal_type = request["mealType"]
    
    # Your logic here
    # Query ChromaDB, calculate scores, sort
    
    return [
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

### Express (Node.js)
```javascript
app.post('/api/recipes/search', (req, res) => {
  const { ingredients, mealType } = req.body;
  
  // Your logic here
  
  res.json([
    {
      id: 1,
      name: "Scrambled Eggs",
      // ... rest of fields
    }
  ]);
});
```

---

## Common Questions

**Q: Where's the database?**
A: Not in frontend. It's on your backend. Frontend just calls your API.

**Q: Can I test without the backend?**
A: Yes. The mock implementation is already there. Replace when backend is ready.

**Q: What if the API fails?**
A: Frontend returns empty array. User sees "No recipes found".

**Q: Where do AI responses come from?**
A: Currently mock. Connect to Ollama/OpenAI in `chat.config.js` when ready.

**Q: Can I add new recipe fields?**
A: Yes. Add to backend response, then use in `App.jsx` if needed.

**Q: How do I debug?**
A: F12 → Network tab → See all requests/responses. Check console for errors.

---

## Development Workflow

### Day 1: Frontend Ready
```
✓ UI built and working
✓ Mock data working
✓ Filters working
✓ Search working
✓ UI looks perfect
```

### Day 2: You Connect Backend
```
1. Build API endpoint
2. Update recipeService.js
3. Test with curl
4. Test with frontend
5. Done!
```

### Day 3: Go Live
```
1. Backend deployed
2. Frontend API URL updated
3. Environment variables set
4. Test on production
5. Monitor errors
```

---

## Frontend Structure (Inside App.jsx)

The main component has 3 sections:

### 1. State (Data That Changes)
```javascript
const [ingredients, setIngredients] = useState([]);
const [recipes, setRecipes] = useState([]);
const [selectedMealType, setSelectedMealType] = useState("All");
const [messages, setMessages] = useState([]);
```

### 2. Event Handlers (What Happens When User Clicks)
```javascript
handleAddIngredient()      // User types + clicks Add
handleRemoveIngredient()   // User clicks X
handleMealTypeChange()     // User clicks filter
handleSearchRecipes()      // Auto-called when ingredients change
handleRecipeSelect()       // User clicks recipe card
handleSendMessage()        // User sends chat message
```

### 3. Render (What Shows on Screen)
```
Left Panel: Recipe Browser
└─ Header + Title
   Ingredient Input
   Filter Buttons
   Recipe Grid
   └─ Recipe Cards (auto-render from recipes state)
   Empty State (if no recipes)

Right Panel: AI Chat
└─ Welcome Message
   Chat History
   Quick Prompts
   Chat Input
```

**You don't need to edit this.** Just connect the API in `recipeService.js`.

---

## Code Quality

- **Zero TypeScript:** Pure JavaScript
- **Well Commented:** Read the comments!
- **Beginner Friendly:** No complex patterns
- **Single Responsibility:** Each file does one thing
- **Mock Data:** Works offline, swap with API when ready

---

## Deployment

### Development
```bash
pnpm install  # First time
pnpm dev      # Run dev server
```

### Production
```bash
pnpm build    # Creates dist/ folder
# Deploy dist/ to hosting (Vercel, AWS, etc)
```

---

## Troubleshooting

| Problem | Check | Fix |
|---------|-------|-----|
| Blank page | Console (F12) | Check errors |
| API not called | Network tab | Check URL in recipeService.js |
| CORS error | Backend | Add CORS headers |
| Recipe doesn't appear | Response | Check score/tier fields |
| Crash on ingredient add | Console | Check API response format |

---

## Reading Guide

If you want to understand more:

1. **5 min:** This file (you're reading it)
2. **15 min:** Read `FRONTEND_STRUCTURE_FOR_BACKEND.md`
3. **30 min:** Read comments in `src/app/App.jsx`
4. **1 hour:** Read `BACKEND_INTEGRATION_CHECKLIST.md`
5. **2 hours:** Read through all code files in order

Start with #1 and #2. That's enough to connect your API.

---

## Bottom Line

**Your job:** Build an API that:
1. Accepts `{ ingredients, mealType, searchTerm }`
2. Returns array of recipes with `score` and `tier`
3. Sorts by score (highest first)

**Frontend's job:** Call your API and display results.

**Time to integration:** 30 minutes.

---

## Let's Do This 🚀

1. Build your API (use FastAPI or Express examples above)
2. Copy-paste the connection code into `recipeService.js`
3. Run `pnpm dev`
4. Test by adding ingredients
5. Done!

Questions? Check the detailed guides in the repository.

Good luck! 🎉
