# Backend Integration Checklist

For backend developers connecting your API to the frontend.

## Step 1: Understand What the Frontend Expects

### Recipe Search Endpoint

**Current (Mock Implementation):**
```javascript
// In src/app/services/recipeService.js
searchRecipes(ingredients, mealType, searchTerm)
```

**Expected Input:**
```
ingredients: ["eggs", "butter", "milk"]
mealType: "All" OR "Breakfast" OR "Lunch" OR "Dinner"
searchTerm: "" (optional search query)
```

**Expected Output:**
```javascript
[
  {
    // Original recipe fields
    id: 1,
    name: "Scrambled Eggs",
    mealType: "Breakfast",
    coreIngredients: ["eggs", "butter", "salt"],
    instructions: "1. Heat butter\n2. Add eggs\n3. Mix",
    cookTime: 5,
    servings: 2,
    
    // Frontend REQUIRES these fields
    score: 0.9,        // 0 to 1 (how well ingredients match)
    tier: 1,           // 1 = perfect, 2 = missing 1, 3 = missing 2+
    matched: ["eggs", "butter"],    // Ingredients user has
    missing: ["salt"]  // Ingredients user doesn't have
  },
  // ... more recipes, sorted by score (highest first)
]
```

---

## Step 2: Build Your Backend Endpoint

### Option A: FastAPI (Python)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/recipes/search")
async def search_recipes(request: dict):
    """
    Receives: { "ingredients": [...], "mealType": "...", "searchTerm": "..." }
    Returns: [ { recipe with score/tier/matched/missing }, ... ]
    """
    ingredients = request.get("ingredients", [])
    meal_type = request.get("mealType", "All")
    search_term = request.get("searchTerm", "")
    
    # Your logic here:
    # 1. Query ChromaDB with ingredients
    # 2. Calculate scores
    # 3. Sort by relevance
    # 4. Return results
    
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

### Option B: Express.js (Node.js)

```javascript
const express = require('express');
const app = express();
app.use(express.json());

// Enable CORS
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type');
  next();
});

app.post('/api/recipes/search', async (req, res) => {
  const { ingredients, mealType, searchTerm } = req.body;
  
  // Your logic here:
  // 1. Query ChromaDB with ingredients
  // 2. Calculate scores
  // 3. Sort by relevance
  // 4. Return results
  
  const results = [
    {
      id: 1,
      name: 'Scrambled Eggs',
      mealType: 'Breakfast',
      coreIngredients: ['eggs', 'butter'],
      instructions: '...',
      cookTime: 5,
      servings: 2,
      score: 0.9,
      tier: 1,
      matched: ['eggs', 'butter'],
      missing: []
    }
  ];
  
  res.json(results);
});

app.listen(3000, () => console.log('Backend running on port 3000'));
```

---

## Step 3: Update the Frontend Service

### Edit: `src/app/services/recipeService.js`

**Find this function:**
```javascript
export async function searchRecipes(ingredients, mealType, searchTerm) {
  return _mockSearch(ingredients, mealType, searchTerm);
}
```

**Replace with this:**
```javascript
export async function searchRecipes(ingredients, mealType, searchTerm) {
  try {
    // Change this URL to match your backend
    const API_URL = 'http://localhost:3000/api/recipes/search';
    // OR in production:
    // const API_URL = 'https://your-api.com/api/recipes/search';
    
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        ingredients: ingredients,
        mealType: mealType,
        searchTerm: searchTerm
      })
    });
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    const recipes = await response.json();
    return recipes;
    
  } catch (error) {
    console.error('[Recipe Search Error]', error);
    // Return empty array on error (graceful fallback)
    return [];
  }
}
```

---

## Step 4: Test the Connection

### Frontend Debugging

1. **Open browser DevTools:** F12
2. **Go to Network tab:** See all requests
3. **Add ingredient:** Watch the request sent to your backend
4. **Check Response:** Should see your recipes array

### Console Logs (Optional)

Add temporary logging in `src/app/services/recipeService.js`:

```javascript
export async function searchRecipes(ingredients, mealType, searchTerm) {
  console.log('[API] Sending:', { ingredients, mealType, searchTerm });
  
  try {
    const response = await fetch('http://localhost:3000/api/recipes/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ingredients, mealType, searchTerm })
    });
    
    const recipes = await response.json();
    console.log('[API] Received:', recipes);
    return recipes;
    
  } catch (error) {
    console.error('[API Error]', error);
    return [];
  }
}
```

Then in browser console (F12), you'll see:
```
[API] Sending: { ingredients: ["eggs"], mealType: "All", searchTerm: "" }
[API] Received: [ { id: 1, name: "Scrambled Eggs", score: 0.9, ... } ]
```

---

## Step 5: Connect AI Chat (Optional)

If you want real AI responses instead of mock replies:

### In Backend: Add Chat Endpoint

```python
@app.post("/api/chat")
async def chat(request: dict):
    """
    Receives: { "messages": [...] }
    Returns: { "reply": "..." }
    """
    messages = request.get("messages", [])
    
    # Call your Ollama / OpenAI / Claude API here
    # Pass the messages, get back a response
    
    return {
        "reply": "Your AI response here"
    }
```

### In Frontend: Update App.jsx

Find `handleSendMessage()` in `src/app/App.jsx`:

**Before (using mock replies):**
```javascript
function handleSendMessage(e) {
  e.preventDefault();
  
  const userMessage = input.trim();
  setMessages(prev => [...prev, { id: Date.now(), role: "user", content: userMessage }]);
  
  // Pick random mock reply
  const randomReply = AI_FALLBACK_REPLIES[
    Math.floor(Math.random() * AI_FALLBACK_REPLIES.length)
  ];
  
  setMessages(prev => [...prev, { 
    id: Date.now() + 1, 
    role: "assistant", 
    content: randomReply 
  }]);
}
```

**After (using your API):**
```javascript
async function handleSendMessage(e) {
  e.preventDefault();
  
  const userMessage = input.trim();
  setMessages(prev => [...prev, { id: Date.now(), role: "user", content: userMessage }]);
  setInput("");
  
  try {
    const response = await fetch('http://localhost:3000/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: messages })
    });
    
    const data = await response.json();
    
    setMessages(prev => [...prev, { 
      id: Date.now() + 1, 
      role: "assistant", 
      content: data.reply 
    }]);
  } catch (error) {
    console.error('Chat error:', error);
  }
}
```

---

## Step 6: Environment Variables (Production)

For production deployment, use environment variables:

### Create: `.env.local`
```
VITE_API_URL=https://your-api.com
```

### In `src/app/services/recipeService.js`:
```javascript
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000';

export async function searchRecipes(ingredients, mealType, searchTerm) {
  const response = await fetch(`${API_URL}/api/recipes/search`, {
    // ... rest of code
  });
}
```

---

## Common Issues & Solutions

### Issue: "CORS error" / "No 'Access-Control-Allow-Origin' header"

**Solution:** Enable CORS on your backend
```python
# FastAPI
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["*"])

# Express
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  next();
});
```

### Issue: "Network tab shows red X"

**Solution:** 
1. Check backend is running: `netstat -tlnp | grep 3000`
2. Check frontend URL matches backend: `http://localhost:3000`
3. Try accessing URL directly in browser

### Issue: "Score field not in response"

**Solution:** Backend must calculate and include score/tier:
```python
score = len(matched) / len(total_ingredients)
tier = 1 if len(missing) == 0 else (2 if len(missing) == 1 else 3)
```

### Issue: "Recipes appear but don't update on ingredient change"

**Solution:** Make sure your API returns sorted results (highest score first)

### Issue: "Recipes display but search term is ignored"

**Solution:** Backend not filtering by searchTerm. Check:
```python
if search_term:
    recipes = [r for r in recipes if search_term.lower() in r['name'].lower()]
```

---

## Deployment Checklist

- [ ] Backend API deployed to production URL
- [ ] CORS configured for your frontend domain
- [ ] Frontend environment variables updated
- [ ] Test on production: Add ingredient → Check network request
- [ ] Verify response contains all required fields (score, tier, matched, missing)
- [ ] Test error handling: Temporarily stop backend → Verify graceful fallback
- [ ] Monitor: Check browser console for errors in production

---

## Quick Reference: Required Response Shape

```javascript
{
  id: number,                           // Unique identifier
  name: string,                         // Recipe name
  mealType: "Breakfast"|"Lunch"|"Dinner",  // Must match filter
  coreIngredients: string[],           // Array of ingredient names
  instructions: string,                // Step-by-step (newlines = "\n")
  cookTime: number,                    // Minutes
  servings: number,                    // Number of people
  
  // REQUIRED by frontend:
  score: number,                       // 0 to 1
  tier: 1|2|3,                        // 1=perfect, 2=missing1, 3=missing2+
  matched: string[],                  // User's ingredients in this recipe
  missing: string[]                   // Ingredients user doesn't have
}
```

---

## API Contract (OpenAPI/Swagger Format)

```yaml
/api/recipes/search:
  post:
    summary: Search recipes by ingredients
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              ingredients:
                type: array
                items: string
                example: ["eggs", "butter"]
              mealType:
                type: string
                enum: ["All", "Breakfast", "Lunch", "Dinner"]
              searchTerm:
                type: string
                example: ""
    responses:
      200:
        description: Array of recipes ranked by match score
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                properties:
                  id: integer
                  name: string
                  mealType: string
                  coreIngredients: array
                  instructions: string
                  cookTime: integer
                  servings: integer
                  score: number
                  tier: integer
                  matched: array
                  missing: array
```

---

## Next Steps

1. **Build your backend** using the examples above
2. **Test locally:** Run both frontend and backend on localhost
3. **Update API URL:** Change `http://localhost:3000` in recipeService.js
4. **Test the flow:** Add ingredient → See updated recipes
5. **Deploy:** Push to production and update environment variables
6. **Monitor:** Check browser console and backend logs

You're all set! The frontend is ready. Now connect it to your backend. 🎉
