# ChromaDB setup

Run these commands in PowerShell:

```powershell
cd C:\path\to\LetThemCook-Capstone-main
python -m pip install -r backend\requirements.txt
ollama pull all-minilm
ollama pull llama3.2:3b
python backend\update_database.py
python backend\build_chroma.py
python -m uvicorn Main:app --app-dir backend --reload
```

If an older ChromaDB build is corrupt, stop the backend and remove only the generated
`backend\chroma_db` directory before running `build_chroma.py` again.

Expected indexing message:

```text
ChromaDB indexed 429 recipes.
```

Check:

```text
http://127.0.0.1:8000/health
```

The response should show `"chroma_ready": true`, `"chroma_query_ready": true`,
and `"chroma_records": 429`.

`llama3.2:3b` generates the answer. `all-minilm` creates local embeddings for ChromaDB.
