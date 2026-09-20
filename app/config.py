"""
Читает настройки из .env и делает их доступными через объект settings.
"""
import os
from dotenv import load_dotenv

# Загружаем .env из корня проекта
load_dotenv()


class Settings:
    # LLM
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Сервер
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Playwright
    HEADLESS: bool = os.getenv("HEADLESS", "true").lower() == "true"
    TN_TIMEOUT_SEC: int = int(os.getenv("TN_TIMEOUT_SEC", "45"))

    def validate(self) -> None:
        """Проверяет, что ключевые настройки на месте."""
        if not self.OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY не задан. Заполни .env (см. .env.example)."
            )


settings = Settings()