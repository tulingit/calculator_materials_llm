"""
Разведчик схемы калькулятора SHINGLAS.

Заходит на tn.ru один раз, кликает по каждому типу крыши
и смотрит, какие поля ввода появляются. Результат кэшируется в памяти
на несколько часов, чтобы не гонять браузер на каждый запрос.

Что возвращает:
{
  "roof_types": {
    "one_slope": {
      "title": "Односкатная",
      "fields": ["square", "angle", "eaves_len", ...]
    },
    ...
  }
}
"""
import asyncio
import logging
import time
from typing import Any, Dict

from playwright.async_api import async_playwright

from app.config import settings

log = logging.getLogger("tn_schema")

# Кэш: хранит результат и время последнего обновления
_cache: Dict[str, Any] = {"data": None, "ts": 0}
CACHE_TTL_SEC = 4 * 60 * 60  # обновляем раз в 4 часа


# Наш код → название карточки на сайте
ROOF_TYPE_MAP = {
    "one_slope": "Односкатная",
    "two_slope": "Двускатная",
    "hip": "Вальмовая",
    "tent": "Шатровая",
    "attic": "Мансардная",
    "complex": "Сложная",
}

# Человеческие названия полей, как они видны клиенту на tn.ru
FIELD_LABELS = {
    "square": "Площадь кровли, м2",
    "angle": "Угол скатов, градусы",
    "apex_len": "Длина коньков, м",
    "eaves_len": "Длина карнизов, м",
    "fasciaboard_len": "Длина ендов, м",
    "eaves_width": "Ширина карнизного вылета, м",
    "ridge_len": "Длина рёбер, м",
    "pediment_len": "Длина фронтонов, м",
    "junc_len": "Длина примыканий, м",
    "walls_thick": "Толщина стены, м",
}

EXTRA_PARAMS = [
    {
        "id": "brickchimney",
        "label": "Есть кирпичная труба",
        "subfields": [
            {"id": "brickchimney_cnt", "label": "Количество труб"},
            {"id": "brickchimney_area", "label": "Общая площадь труб, м2"},
            {"id": "brickchimney_perimeter", "label": "Общий периметр труб, м"},
        ],
    },
    {
        "id": "dormerwindow",
        "label": "Есть мансардное окно",
        "subfields": [
            {"id": "dormerwindow_area", "label": "Общая площадь мансардных окон, м2"},
        ],
    },
    {
        "id": "sewerage",
        "label": "Есть канализационный выход",
        "subfields": [
            {"id": "sewerage_fan", "label": "Количество канализационных выходов"},
            {"id": "yearound", "label": "Всесезонное проживание"},
        ],
    },
    {
        "id": "aerators",
        "label": "Есть точечные аэраторы",
        "subfields": [
            {"id": "aerators_cnt", "label": "Количество точечных аэраторов"},
        ],
    },
]

async def get_schema() -> Dict[str, Any]:
    """
    Возвращает схему калькулятора.
    Если кэш свежий — отдаёт мгновенно.
    Если устарел — заново обходит tn.ru.
    """
    now = time.time()
    if _cache["data"] and (now - _cache["ts"]) < CACHE_TTL_SEC:
        log.info("schema: отдаю из кэша")
        return _cache["data"]

    log.info("schema: обновляю через Playwright")
    try:
        data = await _build_schema()
        _cache["data"] = data
        _cache["ts"] = now
        return data
    except Exception as e:
        log.exception("schema: не удалось обновить")
        if _cache["data"]:
            log.warning("schema: возвращаю устаревший кэш")
            return _cache["data"]
        raise


async def _build_schema() -> Dict[str, Any]:
    """Открывает tn.ru и обходит каждый тип крыши."""
    result: Dict[str, Any] = {"roof_types": {}}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=settings.HEADLESS)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
            locale="ru-RU",
        )
        page = await context.new_page()

        try:
            await page.goto(
                "https://www.tn.ru/calculators/shinglas/",
                timeout=settings.TN_TIMEOUT_SEC * 1000,
                wait_until="domcontentloaded",
            )
            await page.wait_for_load_state(
                "networkidle", timeout=settings.TN_TIMEOUT_SEC * 1000
            )
            await page.wait_for_selector(".quiz__slide", timeout=60000)

            for code, title in ROOF_TYPE_MAP.items():
                try:
                    fields = await _probe_roof_type(page, title)
                    result["roof_types"][code] = {
                        "title": title,
                        "fields": fields,
                    }
                    log.info(f"schema: {code} → поля {fields}")
                except Exception as e:
                    log.warning(f"schema: тип {code} не удалось разведать: {e}")
                    result["roof_types"][code] = {"title": title, "fields": []}

        finally:
            await context.close()
            await browser.close()

    return {
            "roof_types": result["roof_types"],
            "extra_params": EXTRA_PARAMS,
        }


async def _probe_roof_type(page, title: str) -> list:
    """
    Кликает по типу крыши и собирает, какие поля появились в форме.
    Возвращает список id полей (кроме служебных).
    """
    # Возвращаемся на верх формы и кликаем по типу
    await page.goto(
        "https://www.tn.ru/calculators/shinglas/",
        timeout=settings.TN_TIMEOUT_SEC * 1000,
        wait_until="domcontentloaded",
    )
    await page.wait_for_selector(".quiz__slide", timeout=30000)
    await page.click(f".quiz__slide:has-text('{title}')")
    await page.wait_for_timeout(1500)

    # Ждём появления формы размеров
    try:
        await page.wait_for_selector(".tn-calculatorshinglas-calc", timeout=15000)
    except Exception:
        return []

    # Собираем id всех видимых числовых input'ов в форме
    fields = await page.evaluate(
        """() => {
        const known = [
            'square', 'angle', 'apex_len', 'eaves_len', 'fasciaboard_len',
            'eaves_width', 'ridge_len', 'pediment_len', 'junc_len', 'walls_thick'
        ];
        const out = [];
        for (const id of known) {
            const el = document.getElementById(id);
            if (el) out.push(id);
        }
        return out;
    }"""
    )

    # Оборачиваем в словари с человеческими названиями
    return [
        {"id": f, "label": FIELD_LABELS.get(f, f)}
        for f in fields
    ]


def get_required_fields(roof_type: str) -> list:
    """
    Синхронный хелпер: возвращает список обязательных полей
    для конкретного типа крыши из уже закэшированной схемы.
    Если кэша нет — возвращает безопасный дефолт.
    """
    data = _cache.get("data")
    if not data:
        return []
    return data.get("roof_types", {}).get(roof_type, {}).get("fields", [])