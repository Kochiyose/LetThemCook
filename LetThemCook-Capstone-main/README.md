# LetThemCook Capstone

Cleaned full-stack version of **LetThemCook** with:

- React + Vite frontend
- FastAPI backend
- Validated local CSV recipe database connected through FastAPI and ChromaDB
- Local Ollama support for database-grounded Chef Llama chat

## Project structure

```text
LetThemCook-Capstone-main/
├─ backend/
│  ├─ Main.py
│  ├─ chroma_store.py
│  ├─ build_chroma.py
│  ├─ update_database.py
│  ├─ requirements.txt
│  └─ data/
│     └─ LetThemCook_Cleaned.csv         # validated recipe database
├─ frontend/
│  ├─ src/
│  │  └─ app/
│  │     ├─ App.jsx
│  │     └─ services/
│  │        └─ recipeService.js          # API connection
│  └─ package.json
├─ docs/
│  ├─ frontend-handoff/                  # old handoff notes moved here
│  └─ frontend-assets/                   # unused imported design assets
└─ package.json
```

## Run frontend and backend in the same Terminal

cd C:\Users\jayta\Desktop\LetThemCook\LetThemCook-Capstone-main

  npm install
  npm run install:frontend
  python -m pip install -r backend/requirements.txt

  ollama pull llama3.2:3b
  ollama pull all-minilm

  python backend/update_database.py
  python backend/build_chroma.py

  npm run dev

Then open:

```text
http://localhost:5173/
```

The backend will run at:

```text
http://127.0.0.1:8000
```

## API endpoints

```text
GET  /health
GET  /api/recipes/all
GET  /api/recipes/{id}
POST /api/recipes/search
POST /api/chat
POST /api/generate-recipe
```

Example search body:

```json
{
  "pantry": ["chicken", "garlic", "soy sauce"],
  "mealFilter": "All",
  "nameQuery": ""
}
```

## Ollama setup

The checked-in example configuration uses Ollama for local chat and embeddings. If
Ollama becomes unavailable, recipe search falls back to the validated CSV.

To enable Ollama in PowerShell before starting the backend:

```powershell
$env:USE_OLLAMA="true"
$env:OLLAMA_MODEL="llama3.2:3b"
python -m uvicorn Main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Make sure Ollama is already running and the model exists:

```powershell
ollama list
ollama run llama3.2:3b
```

## What was cleaned

- Removed the empty duplicate nested project folder.
- Moved old handoff/documentation files into `docs/frontend-handoff/`.
- Moved unused imported screenshots/design assets into `docs/frontend-assets/`.
- Moved the CSV database into `backend/data/`.
- Fixed the backend CSV path and CORS setup.
- Removed the backend pandas dependency by using Python's built-in CSV reader.
- Connected the UI search and chat services to the FastAPI database endpoints.
- Added CSV validation and deterministic database-grounded fallbacks.
