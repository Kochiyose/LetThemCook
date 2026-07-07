# LetThemCook Frontend

React + Vite UI for the LetThemCook capstone app.

The frontend is connected to the FastAPI backend through:

```text
src/app/services/recipeService.js
```

The backend API base URL comes from:

```text
VITE_API_URL=http://127.0.0.1:8000
```

## Run only the frontend

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173/
```

## Data flow

1. UI calls `searchRecipes()` in `src/app/services/recipeService.js`.
2. `searchRecipes()` sends a POST request to `http://127.0.0.1:8000/api/recipes/search`.
3. The FastAPI backend reads `backend/data/LetThemCook_Core_Database.csv`.
4. Backend returns ranked recipe results to the UI.
5. If the backend is not running, the frontend falls back to `src/app/data/recipes.mock.json`.

## Main editable files

```text
src/app/App.jsx                  # main UI layout
src/app/config/chat.config.js    # chat labels/prompts
src/app/config/ui.config.js      # UI labels/text
src/app/services/recipeService.js# backend API connection
src/styles/                      # styling
```

Do not edit `recipes.mock.json` manually unless you only want to change frontend fallback data. The main mock database is in the backend CSV.
