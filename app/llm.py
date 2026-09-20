"""
Обёртка над OpenAI SDK.
Работает с любым OpenAI-совместимым API.
"""
from openai import AsyncOpenAI
from app.config import settings

# Создаём клиента один раз
_client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL,
)


async def chat(messages: list, tools: list | None = None):
    """
    Отправляет сообщения в LLM.
    Если переданы tools — модель может вызвать tool_calls.
    Возвращает объект ответа (message).
    """
    response = await _client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto" if tools else None,
        temperature=0.2,  # меньше креатива — стабильнее ведёт диалог
    )
    return response.choices[0].message