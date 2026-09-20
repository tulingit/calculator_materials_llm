"""
Хранилище диалогов.
Пока in-memory (словарь). При перезапуске сервера всё теряется.
Позже заменим на Redis.
"""
import time
import uuid
from typing import Dict, List


# Глобальный словарь: session_id -> список сообщений
# Формат сообщения совпадает с OpenAI Chat Completions:
#   {"role": "system"|"user"|"assistant"|"tool", "content": "...", ...}
_sessions: Dict[str, List[dict]] = {}

# Когда последний раз обращались к сессии (для автоочистки)
_last_seen: Dict[str, float] = {}

# Через сколько секунд бездействия удалять сессию (2 часа)
SESSION_TTL_SEC = 2 * 60 * 60


def create_session() -> str:
    """Создаёт новую сессию и возвращает её ID."""
    session_id = uuid.uuid4().hex
    _sessions[session_id] = []
    _last_seen[session_id] = time.time()
    _cleanup()
    return session_id


def get_history(session_id: str) -> List[dict]:
    """Возвращает историю сообщений сессии."""
    _last_seen[session_id] = time.time()
    return _sessions.setdefault(session_id, [])


def append(session_id: str, message: dict) -> None:
    """Добавляет сообщение в историю сессии."""
    _last_seen[session_id] = time.time()
    _sessions.setdefault(session_id, []).append(message)


def reset(session_id: str) -> None:
    """Очищает историю сессии, сохраняя ID."""
    _sessions[session_id] = []
    _last_seen[session_id] = time.time()


def _cleanup() -> None:
    """Удаляет старые сессии."""
    now = time.time()
    to_delete = [
        sid for sid, ts in _last_seen.items() if now - ts > SESSION_TTL_SEC
    ]
    for sid in to_delete:
        _sessions.pop(sid, None)
        _last_seen.pop(sid, None)