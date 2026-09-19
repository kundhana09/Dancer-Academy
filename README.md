# Taalika Dance Academy

A complete Streamlit prototype for an AI-powered dance academy website. It includes course discovery, weekly schedules, instructor profiles, fee details, events, admission capture with the dancer's area, a studio location page with directions, and a local RAG-style assistant scoped to dancers and dance-training questions.

## Run locally

```powershell
python -m pip install -r requirements.txt
uvicorn backend:app --reload --port 8000
```

In a second terminal, start the Streamlit website:

```powershell
streamlit run app.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`.

The backend API runs at `http://localhost:8000`. It creates `taalika.db` automatically, stores admission requests in SQLite, and serves the retrieval-backed chatbot. Set `TAALIKA_API_URL` if the API is hosted elsewhere.

The website's `Visit Us` page shows the studio at 24 Lotus Lane, Indiranagar, Bengaluru and links to Google Maps. The assistant answers academy and dance-training questions; unrelated questions receive a short scope response.

## RAG extension point

The backend assistant uses deterministic token-overlap retrieval over `KNOWLEDGE_BASE` in `backend.py`, so it works without API keys. To connect a production RAG pipeline, replace `retrieve_context()` with a vector-store query and pass the retrieved chunks to your chosen LLM in `answer_question()`.

Suggested production upgrades:

- Move academy content into JSON, Markdown, or a database.
- Add embeddings with Chroma, FAISS, or a managed vector database.
- Add an LLM provider and keep retrieved chunks in the prompt context.
- Persist admission submissions to a database and add authentication for staff.
