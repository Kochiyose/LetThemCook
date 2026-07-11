# ChromaDB setup

Run these commands in PowerShell:

```powershell
cd C:\Users\jayta\Desktop\LetThemCook\LetThemCook-Capstone-main\backend
python -m pip install -r requirements.txt
ollama pull all-minilm
python build_chroma.py
python -m uvicorn Main:app --reload
```

Expected indexing message:

```text
ChromaDB indexed 459 recipes.
```

Check:

```text
http://127.0.0.1:8000/health
```

The response should show `"chroma_ready": true` and `"chroma_records": 459`.

`llama3.2` generates the answer. `all-minilm` creates local embeddings for ChromaDB.
