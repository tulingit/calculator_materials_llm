"""
Объявление tools для LLM.
Модель использует их, чтобы вызывать наш код.
"""
from typing import Any, Dict
from app.adapters import tn_shinglas
from app.adapters import tn_schema

# --- Описание tools в формате OpenAI ---

TOOLS_SPEC1 = [
    {
        "type": "function",
        "function": {
            "name": "run_tn_shinglas",
            "description": (
                "Запускает реальный расчёт гибкой черепицы SHINGLAS на сайте "
                "ТЕХНОНИКОЛЬ. Используй этот tool ТОЛЬКО когда собраны все "
                "обязательные поля: roof_type, collection, color, square, angle, "
                "apex_len, eaves_len. Не вызывай его вслепую."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "roof_type": {
                        "type": "string",
                        "enum": [
                            "one_slope", "two_slope", "hip",
                            "tent", "attic", "complex",
                        ],
                        "description": "Тип крыши",
                    },
                    "collection": {
                        "type": "string",
                        "description": (
                            "Коллекция черепицы (например, 'Ультра Фристайл'). "
                            "Передавай русское название как есть."
                        ),
                    },
                    "color": {
                        "type": "string",
                        "description": (
                            "Цвет черепицы (например, 'Галька', 'Гранит'). "
                            "Передавай русское название как есть."
                        ),
                    },
                    "square": {
                        "type": "number",
                        "description": "Площадь кровли, м²",
                    },
                    "angle": {
                        "type": "number",
                        "description": "Угол скатов, градусы",
                    },
                    "apex_len": {
                        "type": "number",
                        "description": "Длина коньков, м",
                    },
                    "eaves_len": {
                        "type": "number",
                        "description": "Длина карнизов, м",
                    },
                    "pediment_len": {
                        "type": "number",
                        "description": "Длина фронтонов, м (опционально)",
                    },
                    "walls_thick": {
                        "type": "number",
                        "description": "Толщина стены, м (опционально, по умолчанию 0.5)",
                    },
                     "brickchimney": {
                         "type": "boolean",
                         "description": "Есть ли на крыше кирпичная труба",
                    },
                    "brickchimney_cnt": {
                        "type": "integer",
                        "description": "Количество кирпичных труб",
                    },
                    "brickchimney_area": {
                        "type": "number",
                        "description": "Общая площадь кирпичных труб, м²",
                    },
                    "brickchimney_perimeter": {
                        "type": "number",
                        "description": "Общий периметр кирпичных труб, м",
                    },
                    "dormerwindow": {
                        "type": "boolean",
                        "description": "Есть ли мансардное окно",
                    },
                    "dormerwindow_area": {
                        "type": "number",
                        "description": "Общая площадь мансардных окон, м²",
                    },
                    "sewerage": {
                        "type": "boolean",
                        "description": "Есть ли канализационный выход",
                    },
                    "sewerage_fan": {
                        "type": "integer",
                        "description": "Количество канализационных выходов",
                    },
                    "yearound": {
                        "type": "boolean",
                        "description": "Всесезонное проживание (для выбора модели вентвыхода)",
                    },
                    "aerators": {
                        "type": "boolean",
                        "description": "Есть ли точечные аэраторы",
                    },
                    "aerators_cnt": {
                        "type": "integer",
                        "description": "Количество точечных аэраторов",
                    },
                },
                "required": [
                    "roof_type", "collection", "color",
                    "square", "angle", "apex_len", "eaves_len",
                ],
            },
        },
    },
]

TOOLS_SPEC = [
    # --- Tool 1: схема калькулятора ---
    {
        "type": "function",
        "function": {
            "name": "get_calculator_schema",
            "description": (
                "Возвращает список доступных опций калькулятора SHINGLAS: "
                "какие типы крыши есть и какие поля нужно спрашивать "
                "у клиента для каждого типа. Вызывай этот tool ПЕРВЫМ, "
                "прежде чем задавать клиенту вопросы про поля."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },

    # --- Tool 2: расчёт ---
    {
        "type": "function",
        "function": {
            "name": "run_tn_shinglas",
            "description": (
                "Запускает реальный расчёт гибкой черепицы SHINGLAS. "
                "Используй ТОЛЬКО когда собраны все обязательные поля "
                "для выбранного типа крыши (см. результат "
                "get_calculator_schema)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "roof_type": {
                        "type": "string",
                        "enum": ["one_slope", "two_slope", "hip", "tent", "attic", "complex"],
                        "description": "Тип крыши",
                    },
                    "collection": {
                        "type": "string",
                        "description": "Название коллекции, как в схеме",
                    },
                    "color": {
                        "type": "string",
                        "description": "Цвет черепицы, как назвал клиент",
                    },
                    "square": {
                        "type": "number",
                        "description": "Площадь кровли, м2",
                    },
                    "angle": {
                        "type": "number",
                        "description": "Угол скатов, градусы",
                    },
                    "apex_len": {
                        "type": "number",
                        "description": "Длина коньков, м",
                    },
                    "eaves_len": {
                        "type": "number",
                        "description": "Длина карнизов, м",
                    },
                    "fasciaboard_len": {
                        "type": "number",
                        "description": "Длина ендов, м",
                    },
                    "eaves_width": {
                        "type": "number",
                        "description": "Ширина карнизного вылета, м",
                    },
                    "ridge_len": {
                        "type": "number",
                        "description": "Длина рёбер, м",
                    },
                    "pediment_len": {
                        "type": "number",
                        "description": "Длина фронтонов, м",
                    },
                    "junc_len": {
                        "type": "number",
                        "description": "Длина примыканий, м",
                    },
                    "walls_thick": {
                        "type": "number",
                        "description": "Толщина стены, м",
                    },
                    "brickchimney": {
                        "type": "boolean",
                        "description": "Есть ли на крыше кирпичная труба",
                    },
                    "brickchimney_cnt": {
                        "type": "integer",
                        "description": "Количество кирпичных труб",
                    },
                    "brickchimney_area": {
                        "type": "number",
                        "description": "Общая площадь кирпичных труб, м2",
                    },
                    "brickchimney_perimeter": {
                        "type": "number",
                        "description": "Общий периметр кирпичных труб, м",
                    },
                    "dormerwindow": {
                        "type": "boolean",
                        "description": "Есть ли мансардное окно",
                    },
                    "dormerwindow_area": {
                        "type": "number",
                        "description": "Общая площадь мансардных окон, м2",
                    },
                    "sewerage": {
                        "type": "boolean",
                        "description": "Есть ли канализационный выход",
                    },
                    "sewerage_fan": {
                        "type": "integer",
                        "description": "Количество канализационных выходов",
                    },
                    "yearound": {
                        "type": "boolean",
                        "description": "Всесезонное проживание (для выбора типа вентвыхода)",
                    },
                    "aerators": {
                        "type": "boolean",
                        "description": "Есть ли точечные аэраторы",
                    },
                    "aerators_cnt": {
                        "type": "integer",
                        "description": "Количество точечных аэраторов",
                    },
                },
                "required": ["roof_type", "collection", "color"],
            },
        },
    },
]

async def call_tool1(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Роутер: какой tool вызван → какой код выполнять.
    Возвращает dict, который мы потом сериализуем в JSON для LLM.
    """
    if name == "run_tn_shinglas":
        # Запускаем реальный Playwright-адаптер
        result = await tn_shinglas.calculate(arguments)
        return result

    return {"ok": False, "error": f"Неизвестный tool: {name}"}

async def call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Роутер: какой tool вызван → какой код выполнять."""

    if name == "get_calculator_schema":
        schema = await tn_schema.get_schema()
        return {"ok": True, "schema": schema}

    if name == "run_tn_shinglas":
        # Проверяем, что все нужные поля есть — используем свежую схему
        try:
            schema = await tn_schema.get_schema()
            required = (
                schema.get("roof_types", {})
                .get(arguments.get("roof_type"), {})
                .get("fields", [])
            )
            missing = [f for f in required if arguments.get(f) is None]
            # Разрешаем отсутствие "walls_thick" и "eaves_width" — 
            # у них есть дефолты на сайте
            missing = [m for m in missing if m not in ("walls_thick", "eaves_width")]
            if missing:
                return {
                    "ok": False,
                    "error": f"Не хватает полей для этого типа крыши: {missing}",
                }
        except Exception:
            pass  # если schema недоступна — не блокируем расчёт

        result = await tn_shinglas.calculate(arguments)
        return result

    return {"ok": False, "error": f"Неизвестный tool: {name}"}