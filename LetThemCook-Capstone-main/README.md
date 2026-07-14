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

This application consists of three components that must be running simultaneously: the **AI Engine (Ollama)**, the **FastAPI Backend**, and the **React Frontend**.

### Step 1: Start the AI Engine (Ollama)
The chatbot relies strictly on a local AI model for all reasoning and conversation. If Ollama is offline, the system will explicitly report that the Kitchen Assistant is unavailable.

1. Ensure [Ollama](https://ollama.com/) is installed and running on your system.
2. Open a terminal and download the required models:
   ```powershell
   ollama pull llama3.2:3b
   ollama pull all-minilm
   ```
3. Keep the Ollama application running in the background.

### Step 2: Set up and Start the Backend
The backend serves the recipes and communicates with ChromaDB and Ollama.

1. Open a new PowerShell terminal.
2. Navigate to the project folder:
   ```powershell
   cd C:\Users\jayta\Desktop\LetThemCook\LetThemCook-Capstone-main
   ```
3. Install Python dependencies:
   ```powershell
   python -m pip install -r backend/requirements.txt
   ```
4. Build the vector database (ChromaDB) from the CSV data:
   ```powershell
   python backend/update_database.py
   python backend/build_chroma.py
   ```
5. Enable the Ollama configuration and start the backend server:
   ```powershell
   $env:USE_OLLAMA="true"
   $env:OLLAMA_MODEL="llama3.2:3b"
   python -m uvicorn Main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
   ```
6. The backend is now running at `http://127.0.0.1:8000`. Leave this terminal open.

### Step 3: Start the Frontend
The frontend provides the interactive UI for the user.

1. Open another new PowerShell terminal.
2. Navigate to the project folder:
   ```powershell
   cd C:\Users\jayta\Desktop\LetThemCook\LetThemCook-Capstone-main
   ```
3. Install Node.js dependencies:
   ```powershell
   npm install
   npm run install:frontend
   ```
4. Start the frontend development server:
   ```powershell
   npm run dev
   ```
5. Open your web browser and navigate to:
   ```text
   http://localhost:5173/
   ```

---

## API Endpoints

The FastAPI backend exposes the following routes:

- `GET  /health` : Checks system status (ChromaDB, Ollama, and CSV loaded).
- `GET  /api/recipes/all` : Returns all recipes.
- `GET  /api/recipes/{id}` : Returns a specific recipe.
- `POST /api/recipes/search` : Semantic RAG search for recipes.
- `POST /api/chat` : General chatbot interface (requires Ollama).
- `POST /api/generate-recipe` : Structured recipe generation (requires Ollama).
