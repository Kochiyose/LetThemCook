# LetThemCook Capstone

A local, web-based AI Chatbot Meal Recommendation and Recipe Catalog.
This project uses **Retrieval-Augmented Generation (RAG)** through **ChromaDB** and the **Llama 3.2** model to provide strict, dataset-grounded cooking instructions without hallucination.

## Project Structure

```text
LetThemCook-Capstone-main/
├─ backend/
│  ├─ Main.py
│  ├─ chroma_store.py
│  ├─ build_chroma.py
│  ├─ update_database.py
│  ├─ requirements.txt
│  └─ data/
│     └─ LetThemCook_Cleaned.csv         # Validated recipe database
├─ frontend/
│  ├─ src/
│  │  └─ app/
│  │     ├─ App.jsx
│  │     └─ services/
│  │        └─ recipeService.js          # Backend API connection
│  └─ package.json
└─ package.json
```

---

## 🚀 How to Run the Application

Use one PowerShell window from the project root. Make sure Ollama is installed and running, then run:

```powershell
cd C:\Users\jayta\Documents\GitHub\Sample\LetThemCook-Capstone-main

if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\Activate.ps1

python -m pip install -r backend\requirements.txt
npm install
npm run install:frontend

ollama pull llama3.2:3b
ollama pull all-minilm

python backend\update_database.py
python backend\build_chroma.py

npm run dev
```

The last command starts both the FastAPI backend and React frontend in the same PowerShell window. Open `http://localhost:5173/` in your browser. Press `Ctrl+C` in that window to stop both servers.

---

## API Endpoints

The FastAPI backend exposes the following routes:

- `GET  /health` : Checks system status (ChromaDB, Ollama, and CSV loaded).
- `GET  /api/recipes/all` : Returns all recipes.
- `GET  /api/recipes/{id}` : Returns a specific recipe.
- `POST /api/recipes/search` : Semantic RAG search for recipes.
- `POST /api/chat` : Grounded recipe recommendations and cooking chat.
- `POST /api/generate-recipe` : Structured, dataset-grounded recipe generation.
