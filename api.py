"""FastAPI backend: chat API + serves the built React website.

Run locally:   python api.py           -> http://127.0.0.1:7860
API docs:      http://127.0.0.1:7860/docs
"""
import json
import mimetypes
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import iterate_in_threadpool

import config
from src.chatbot import Chatbot
from src.guard import RateLimiter

state: dict = {}

# Windows sometimes reports .js files as "text/plain", which makes browsers refuse to run the
# website (blank page). Set the correct types explicitly.
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("font/woff2", ".woff2")


@asynccontextmanager
async def lifespan(app: FastAPI):
    bot = state.get("bot") or Chatbot()          # tests can inject their own bot
    bot.retriever.warm_up()                       # load models before the first visitor
    state["bot"] = bot
    state["limiter"] = RateLimiter()
    yield
    state.clear()


app = FastAPI(title=f"Chat with {config.OWNER_NAME}", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS,
                   allow_methods=["GET", "POST"], allow_headers=["*"])


# ── models ───────────────────────────────────────────────────────────────
class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=config.MAX_QUESTION_CHARS * 2)
    history: list[Message] = Field(default_factory=list, max_length=40)


# ── helpers ──────────────────────────────────────────────────────────────
def visitor_id(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")     # set by Hugging Face / proxies
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


# ── API routes ───────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    bot = state.get("bot")
    return {"status": "ok", "chunks": len(bot.retriever.chunks) if bot else 0,
            "reranker": bool(bot and bot.retriever.reranker)}


@app.get("/api/meta")
def meta():
    """Information the website shows: name, role, links, suggested questions."""
    return {"name": config.OWNER_NAME, "first_name": config.OWNER_FIRST_NAME,
            "role": config.OWNER_ROLE, "links": config.OWNER_LINKS,
            "suggestions": config.SUGGESTED_QUESTIONS, "max_chars": config.MAX_QUESTION_CHARS}


@app.post("/api/chat")
def chat(body: ChatRequest, request: Request):
    """Streams the answer as Server-Sent Events (one JSON object per `data:` line)."""
    if not state["limiter"].allow(visitor_id(request)):
        raise HTTPException(status_code=429,
                            detail="You're sending messages very quickly. Please wait a minute and try again.")
    history = [m.model_dump() for m in body.history]
    events = state["bot"].stream_events(body.message, history)
    return StreamingResponse(iterate_in_threadpool(sse(e) for e in events),
                             media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── website (built React app) ────────────────────────────────────────────
if (config.FRONTEND_DIST / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=config.FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def website(path: str):
        file = (config.FRONTEND_DIST / path).resolve()
        if path and file.is_file() and config.FRONTEND_DIST.resolve() in file.parents:
            return FileResponse(file)
        return FileResponse(config.FRONTEND_DIST / "index.html")
else:
    @app.get("/", include_in_schema=False)
    def no_website():
        return {"message": "API is running. Build the website with: cd frontend && npm install && npm run build"}


if __name__ == "__main__":
    import uvicorn
    print(f"\n  Open http://127.0.0.1:{config.PORT} in your browser  (Ctrl + C to stop)\n")
    uvicorn.run("api:app", host="127.0.0.1", port=config.PORT)
