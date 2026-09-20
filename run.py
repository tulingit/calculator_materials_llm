"""
Точка входа приложения.
Запускает FastAPI-сервер через uvicorn.

Использование:
    python run.py
"""
import uvicorn
from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.server:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,          # для продакшена False, для разработки можно True
        log_level="info",
    )