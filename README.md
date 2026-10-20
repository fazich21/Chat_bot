---
title: Ask Faizan
emoji: 🏔️
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# Ask Faizan

A personal RAG chatbot that answers questions about me, M Faizan, using my own documents (CV, bio, projects, skills, FAQ…) as its knowledge base.

**Backend:** FastAPI · BGE-small embeddings · FAISS + BM25 hybrid search · cross-encoder reranking · Groq (`openai/gpt-oss-120b`)
**Frontend:** React 19 · Vite · Tailwind CSS 4 · streaming Markdown answers

## Features

### Retrieval
| Feature | What it does |
|---|---|
| **Reads PDF, Word, Markdown, text** | Drop files into `data/`. Headings are detected from font size (PDF) or styles (Word), so each section becomes its own chunk. |
| **Cleaning + privacy** | Removes page footers, bylines and editing notes. Phone and ID numbers are removed before indexing and again from every answer. |
| **Query rewriting** | "What are **his** interests?" is searched as "What are **my** interests?" to match the first-person documents. |
| **Synonym expansion** | "interests" also searches hobbies/passions/free time; "study" also searches education/university/IUIC, and so on. |
| **Hybrid search** | Meaning-based search (FAISS) + keyword search (BM25), merged with reciprocal rank fusion → 20 candidates. |
| **Cross-encoder reranking** | A second model reads the question and each candidate together and keeps the 7 most relevant. Much more accurate than search alone. |
| **Neighbour chunks + ordering** | Split sections are kept whole, and context is grouped by document so the LLM sees coherent text. |
| **Auto-rebuilding index** | Rebuilt automatically when anything in `data/` changes. |

### Answers
| Feature | What it does |
|---|---|
| **Structured answers** | A direct opening line, then bullet lists with **bold labels** and concrete details, grouped (e.g. Professional / Personal), and a short closing line. |
| **Covers everything relevant** | The prompt asks the model to combine details from all matching sections, not just the first one. |
| **First-person persona** | Answers as Faizan; says "I don't have that information" instead of guessing. |
| **Follow-ups** | Remembers the last 4 exchanges; short follow-ups are searched with the previous question. |
| **Guard rails** | Blocks prompt injection and over-long messages before calling the API; 10 messages/minute per visitor. |

### Website
| Feature | What it does |
|---|---|
| **Streaming** | Answers appear word by word (Server-Sent Events) with a stop button. |
| **Welcome screen** | Name, role and one-click suggested questions. |
| **Sources** | Each answer shows which of your documents it came from. |
| **Copy, retry, new chat** | Copy an answer, retry after an error, clear the conversation. |
| **Dark mode** | Follows the system setting, with a toggle. |
| **Mobile-friendly** | Works on phones; keyboard and screen-reader friendly. |

### Other
- **Question log**: `logs/questions.jsonl` records every question and whether it was answered, so you know what to add to your documents.
- **API docs** at `/docs` (FastAPI's automatic Swagger page).
- **33 automated tests** that run offline.

## Project structure

```
faizan-chatbot/
├── data/                     ← your documents (.pdf, .docx, .md, .txt)
├── prompts/system_prompt.txt ← persona, rules and answer format
├── src/
│   ├── documents.py          ← read PDF / DOCX / MD / TXT, detect headings
│   ├── cleaning.py           ← remove notes & footers, redact phone/ID numbers
│   ├── chunking.py           ← split into section-sized chunks
│   ├── ingest.py             ← data/ → chunks + data report
│   ├── query.py              ← "his" → "my", synonym expansion
│   ├── retriever.py          ← hybrid search + reranking + index save/load
│   ├── guard.py              ← input checks, rate limiter, output redaction
│   └── chatbot.py            ← retrieve → prompt → stream from Groq → log
├── api.py                    ← FastAPI server (API + serves the website)
├── frontend/                 ← React app (src/) and its build (dist/)
├── scripts/
│   ├── build_index.py        ← check data, show chunks, rebuild index
│   └── ask.py                ← chat in the terminal / run test questions
├── tests/                    ← pytest suite (offline)
├── config.py                 ← all settings
├── Dockerfile                ← for deploying
└── requirements.txt
```

## Run locally (Windows)

You need Python 3.10+. Node.js is only needed if you want to change the website.

```bash
cd "C:\path\to\faizan-chatbot"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Rename `.env.example` to `.env` and put your Groq key in it (`GROQ_API_KEY=gsk_...`).

```bash
python api.py
```

Open **http://127.0.0.1:7860**. The first start downloads the two search models (about 220 MB) and builds the index.

### Changing the website

The website is already built (`frontend/dist`), so you only need this to change its design or code:

```bash
cd frontend
npm install
npm run dev          # live-reloading site at http://localhost:5173 (keep python api.py running)
npm run build        # when done: rebuilds frontend/dist, which api.py serves
```

### Useful commands

```bash
python scripts/build_index.py --check   # check your documents for problems
python scripts/build_index.py --show    # see exactly what the bot reads
python scripts/ask.py --test --sources  # run test questions, show sources and scores
pip install -r requirements-dev.txt
pytest                                  # run the automated tests
```

## Deploy free on Hugging Face Spaces

1. Create a Space at huggingface.co/new-space → SDK **Docker** → template **Blank** → hardware **CPU basic (free)**.
2. **Settings → Variables and secrets** → add secret `GROQ_API_KEY`.
3. Upload the project (or `git push` to the Space). Don't upload `.env`, `venv/` or `frontend/node_modules/`. Do upload `frontend/dist/`.
4. The Space builds the Docker image (about 5–10 minutes the first time) and starts. Your chatbot is at `https://<username>-<space-name>.hf.space`.

The free Space sleeps when nobody uses it; the first visit afterwards takes a little longer. Files on a free Space are temporary, so the question log resets on restart.

## Tuning (`config.py`)

- `SUGGESTED_QUESTIONS`, `OWNER_ROLE`, `OWNER_LINKS`: what the website shows.
- `TOP_K` (7) / `CANDIDATES` (20): how many chunks reach the LLM / the reranker.
- `RERANK_MIN_SCORE`: raise to drop weaker chunks.
- `USE_RERANKER`: set `false` in `.env` to skip reranking (faster, less accurate).
- `MAX_TOKENS`: answer length limit.
- `prompts/system_prompt.txt`: tone and answer format.

If an answer is wrong, fix the document, not the code.
