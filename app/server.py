"""
FastAPI-сервер.
Отдаёт:
  - GET  /              → HTML-виджет
  - POST /api/session   → создать новую сессию
  - POST /api/chat      → отправить сообщение и получить ответ
  - POST /api/reset     → очистить диалог
"""
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app import agent, sessions
from app.config import settings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

# Проверяем .env при старте
settings.validate()

app = FastAPI(title="TN Agent")

# CORS: разрешаем запросы с любого домена (для MVP).
# В продакшене замени "*" на домен вашего сайта.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


# --- Модели запросов ---

class ChatRequest(BaseModel):
    session_id: str
    message: str


class ResetRequest(BaseModel):
    session_id: str


# --- Endpoints ---

@app.get("/")
async def index():
    """Отдаёт HTML виджета для локального теста."""
    return FileResponse(STATIC_DIR / "widget.html")


@app.post("/api/session")
async def create_session():
    """Создаёт новую сессию и возвращает её ID."""
    sid = sessions.create_session()
    return {"session_id": sid}


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """Основной endpoint: принимает сообщение, возвращает ответ агента."""
    if not req.session_id:
        return {"error": "session_id обязателен"}
    if not req.message.strip():
        return {"error": "message пустой"}

    reply = await agent.process_message(req.session_id, req.message)
    return {"reply": reply, "session_id": req.session_id}


@app.post("/api/reset")
async def reset_endpoint(req: ResetRequest):
    """Очищает историю сессии."""
    sessions.reset(req.session_id)
    return {"ok": True}