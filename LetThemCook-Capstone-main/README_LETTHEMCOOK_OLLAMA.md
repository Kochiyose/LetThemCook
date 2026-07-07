# LetThemCook Ollama Dataset Mode

This version keeps Llama focused on LetThemCook and the bundled mock recipe dataset.

## What changed

- `backend/.env` sets `USE_OLLAMA=true` by default.
- The backend now has a hard off-topic guard before it calls Ollama.
- Ollama receives a strict LetThemCook system prompt.
- Recipe-specific answers must use `backend/data/LetThemCook_Core_Database.csv` context.
- If a recipe is not in the dataset, the bot says it was not found instead of inventing one.
- The UI badge now says `Llama 3.2 · LetThemCook Dataset`.

## Before running

Make sure Ollama is installed and the model exists:

```powershell
ollama pull llama3.2
ollama run llama3.2
```

Then in another PowerShell terminal:

```powershell
cd C:\Users\jayta\Desktop\LetThemCook\LetThemCook-Capstone-main
npm install
npm run install:frontend
npm run install:backend
npm run dev
```

Open:

```text
http://localhost:5173/
```

## Check backend mode

Open this in your browser:

```text
http://127.0.0.1:8000/health
```

You should see:

```json
"ollama_enabled": true,
"focus_mode": "LetThemCook dataset + cooking only"
```

## Good tests

```text
hello
```

```text
How to make breakfast steak?
```

```text
What can I make with eggs and butter?
```

```text
What is Roblox?
```

The Roblox question should be refused because it is outside LetThemCook/cooking.
