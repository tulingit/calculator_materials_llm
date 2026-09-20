"""
LLM-агент: основной цикл диалога.

Как работает:
1. Принимает сообщение пользователя.
2. Добавляет его в историю сессии.
3. Вызывает LLM с историей и списком tools.
4. Если LLM вернула tool_calls — выполняет их, кладёт результаты
   обратно в историю и снова вызывает LLM.
5. Когда LLM отвечает простым текстом — возвращает его клиенту.

Правило: LLM НИКОГДА не считает сама. Все цифры приходят из tools.
"""
import json
import logging
from typing import List

from app import sessions
from app.config import settings
from app.llm import chat
from app.tools import TOOLS_SPEC, call_tool


# Системный промпт — задаёт роль и правила поведения.
SYSTEM_PROMPT = """Ты — дружелюбный ассистент компании «Центр СМ».
Ты помогаешь клиентам рассчитать количество гибкой черепицы SHINGLAS.

ПРАВИЛА:
1. Общайся ТОЛЬКО на русском языке.
2. Никогда не считай материалы сам. Все числа приходят из tool
   `run_tn_shinglas`.
3. Никогда не придумывай поля. Единственный источник правды —
   результат tool `get_calculator_schema`.

ПОРЯДОК ДЕЙСТВИЙ:
A. Когда клиент просит посчитать черепицу, вызови tool
   `get_calculator_schema`. Он вернёт список типов крыши
   и список дополнительных параметров.
B. Спроси тип крыши, перечислив варианты.
C. После выбора типа крыши посмотри на список полей для этого типа:
   `schema.roof_types[roof_type].fields`.
D. Спрашивай у клиента ТОЛЬКО те поля, которые есть в этом списке.
   Формулируй вопросы ТОЧНО ТАК, как написано в поле `label`.
   Не переводи, не переименовывай, не объединяй поля.
E. Если поля нет в списке для этого типа крыши — НИКОГДА его
   не спрашивай.
F. Спрашивай по 2-3 поля за раз.
G. Также спроси коллекцию и цвет черепицы.

G+. КОГДА ВСЕ ОСНОВНЫЕ ПОЛЯ СОБРАНЫ, задай ОДИН последний вопрос
    про дополнительные параметры. Возьми список `extra_params`
    из схемы. Сформулируй так:
    «Есть ли на вашей крыше что-то из следующего:
     кирпичная труба, мансардное окно, канализационный выход,
     точечные аэраторы? Если ничего нет — напишите "нет",
     и я сразу посчитаю.»
    НЕ ВЫЗЫВАЙ tool `run_tn_shinglas`, пока не получил ответ
    на этот вопрос.
H. Если клиент ответил «нет» или «ничего нет» — вызывай
   `run_tn_shinglas` только с основными полями.
I. Если клиент назвал что-то из дополнительных параметров —
   уточни ТОЛЬКО по названному, используя `subfields` из схемы.
   Например, для кирпичной трубы: количество, общая площадь, общий
   периметр. Затем передай всё в `run_tn_shinglas`.
J. Покажи клиенту список материалов, как он пришёл из tool.
   Ничего не добавляй и не убирай от себя.

ЗАПРЕЩЕНО:
- Спрашивать «длину свесов», «ширину свесов», «длину торца»,
  «длину фронтона» и любые другие названия, которых нет в схеме.
- Менять формулировки полей из схемы на синонимы.
- Придумывать поля «по логике вещей».
- Вызывать `run_tn_shinglas` до ответа на вопрос про доп. параметры.

Будь кратким. Работай только по схеме.
"""

# Сколько раз максимум прогонять цикл tool-calling (защита от зацикливания)
MAX_TOOL_ITERATIONS = 5


async def process_message(session_id: str, user_message: str) -> str:
    """
    Обрабатывает сообщение пользователя и возвращает ответ агента.
    """
    history = sessions.get_history(session_id)

    # Если это первый запрос в сессии — добавляем системный промпт
    if not history:
        sessions.append(session_id, {"role": "system", "content": SYSTEM_PROMPT})

    # Добавляем сообщение пользователя
    sessions.append(session_id, {"role": "user", "content": user_message})

    # Цикл tool-calling
    for iteration in range(MAX_TOOL_ITERATIONS):
        history = sessions.get_history(session_id)
        message = await chat(history, tools=TOOLS_SPEC)

        # Если модель вызвала tool
        if message.tool_calls:
            # Сохраняем ответ ассистента с tool_calls в историю
            sessions.append(session_id, {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            })

            # Выполняем каждый tool
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                logging.info(f"[agent] tool call: {tc.function.name} args={args}")
                result = await call_tool(tc.function.name, args)

                sessions.append(session_id, {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

            # Возвращаемся к началу цикла: LLM получит результат tool и ответит
            continue

        # Обычный текстовый ответ
        text = (message.content or "").strip() or "Извините, не могу ответить."
        sessions.append(session_id, {"role": "assistant", "content": text})
        return text

    # Если цикл не завершился — что-то пошло не так
    return "Извините, не получилось обработать запрос. Попробуйте переформулировать."