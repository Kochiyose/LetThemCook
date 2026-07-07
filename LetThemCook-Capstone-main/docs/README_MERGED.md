# LetThemCook — Merged Frontend + Backend

This cleaned project separates the app into two clear parts:

```text
LetThemCook_Merged/
├── backend/     # FastAPI Python backend
├── frontend/    # React + Vite frontend
└── package.json # optional root scripts
```

## What was changed

- Moved the Python backend out of the confusing `frontend/frontend` folder.
- Used the bigger LetThemCook React app as the main frontend.
- Connected the chat UI to `POST /api/chat`.
- Connected recipe search to `POST /api/recipes/search`.
- Fixed the broken backend issue where `RecipeQuery` was used before it existed.
- Added a local `recipes.json` backend database so the backend runs even without ChromaDB.
- Removed `node_modules`, cache folders, nested ZIP files, logs, and build junk from the final ZIP.

## First-time install

Open a terminal in this folder:

```powershell
cd LetThemCook_Merged
```

Install the frontend packages:

```powershell
npm install --prefix frontend
```

Install the backend packages:

```powershell
pip install -r backend/requirements.txt
```

## Run the app — easiest way

Terminal 1: backend

```powershell
cd backend
python -m uvicorn Main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2: frontend

```powershell
cd frontend
npm run dev
```

Open:

```text
http://localhost:5173
```

Backend health check:

```text
http://127.0.0.1:8000/health
```

## Optional: run both with one command

Install the root helper package first:

```powershell
npm install
```

Then run:

```powershell
npm run dev
```

## Optional: Ollama / Llama 3.2

The backend will try to call Ollama at:

```text
http://localhost:11434/api/generate
```

using model:

```text
llama3.2
```

If Ollama is not running, the backend still replies using local recipe matching.

To disable Ollama attempts, copy `backend/.env.example` to `backend/.env` and set:

```env
USE_OLLAMA=false
```
