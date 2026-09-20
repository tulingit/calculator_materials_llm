"""
Playwright-адаптер для калькулятора гибкой черепицы SHINGLAS на tn.ru.

Что делает:
1. Открывает https://www.tn.ru/calculators/shinglas/
2. Кликает по типу крыши, коллекции, цвету
3. Заполняет поля размеров
4. Читает результат
5. Возвращает структурированный dict

Селекторы взяты из дампа step_*.html.
Если tn.ru изменит вёрстку — правим селекторы здесь.
"""
import asyncio
import re
from typing import Any, Dict, List

from playwright.async_api import async_playwright, Page

from app.config import settings


# Карта: наш код типа крыши → текст карточки на сайте
ROOF_TYPE_MAP = {
    "one_slope": "Односкатная",
    "two_slope": "Двускатная",
    "hip": "Вальмовая",
    "tent": "Шатровая",
    "attic": "Мансардная",
    "complex": "Сложная",
}


async def calculate(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Главная функция адаптера. Принимает словарь параметров.
    Возвращает словарь с результатом.
    """
    import logging
    log = logging.getLogger("tn_shinglas")

    browser = None
    context = None
    try:
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

            log.info("шаг 1: открываю страницу")
            try:
                return await asyncio.wait_for(
                    _run(page, params, log),
                    timeout=settings.TN_TIMEOUT_SEC,
                )
            except asyncio.TimeoutError:
                log.error(f"ТАЙМАУТ после {settings.TN_TIMEOUT_SEC} сек.")
                return {"ok": False, "error": f"Таймаут {settings.TN_TIMEOUT_SEC} сек."}
            except Exception as e:
                log.exception("ошибка в _run")
                return {"ok": False, "error": f"Ошибка адаптера: {e}"}

    except Exception as e:
        log.exception("ошибка запуска браузера")
        return {"ok": False, "error": f"Ошибка браузера: {e}"}
    finally:
        # Аккуратно закрываем всё, что открыли
        try:
            if context:
                await context.close()
        except Exception:
            pass
        try:
            if browser:
                await browser.close()
        except Exception:
            pass

async def _run(page: Page, params: Dict[str, Any], log) -> Dict[str, Any]:
    """Пошаговый сценарий по сайту tn.ru."""
    # --- 1. Открыть страницу ---
    log.info("1/6 goto")
    await page.goto(
        "https://www.tn.ru/calculators/shinglas/",
        timeout=settings.TN_TIMEOUT_SEC * 1000,
        wait_until="domcontentloaded",
    )

    log.info("1/6 wait networkidle")
    await page.wait_for_load_state("networkidle", timeout=60000)

    log.info("1/6 wait .quiz__slide")
    await page.wait_for_selector(".quiz__slide", timeout=60000)
    log.info("1/6 OK")

    # --- 2. Тип крыши ---
    roof_text = ROOF_TYPE_MAP.get(params["roof_type"])
    if not roof_text:
        raise ValueError(f"Неизвестный тип крыши: {params['roof_type']}")

    log.info(f"2/6 клик по типу крыши: {roof_text}")
    await page.click(f".quiz__slide:has-text('{roof_text}')")
    await page.wait_for_timeout(800)
    log.info("2/6 OK")

    # --- 3. Коллекция ---
    log.info(f"3/6 клик по коллекции: {params['collection']}")
    await page.wait_for_selector(".main-collection-in__link", timeout=30000)
    await page.click(
        f".main-collection-in__link:has-text('{params['collection']}')"
    )
    await page.wait_for_timeout(800)
    log.info("3/6 OK")

    # --- 4. Цвет ---
    if params.get("color"):
        log.info(f"4/6 клик по цвету: {params['color']}")
        try:
            await page.click(
                f".additional_palette_block:has-text('{params['color']}')"
            )
            await page.wait_for_timeout(800)
            log.info("4/6 OK")
        except Exception as e:
            log.warning(f"4/6 цвет не найден: {e}")

    # --- 5. Заполнение полей ---
    #log.info("5/6 заполняю поля")
    #await page.wait_for_selector("#square", timeout=30000)

    #await _fill(page, "#square", params["square"])
    #await _fill(page, "#angle", params.get("angle", 30))
    #await _fill(page, "#apex_len", params.get("apex_len", 0))
    #await _fill(page, "#eaves_len", params.get("eaves_len", 0))

    #if params.get("pediment_len") is not None:
    #    await _fill(page, "#pediment_len", params["pediment_len"])
    #if params.get("walls_thick") is not None:
    #    await _fill(page, "#walls_thick", params["walls_thick"])

    #log.info("5/6 blur")
    #await page.evaluate("document.activeElement && document.activeElement.blur()")

    #log.info("5/6 ждём пересчёт")
    #await page.wait_for_timeout(3000)
    #log.info("5/6 OK")
    
    # --- 5. Заполнение полей ---
    log.info("5/6 заполняю поля")
    await page.wait_for_selector(".tn-calculatorshinglas-calc", timeout=30000)

    # Универсальный список: id поля → ключ в params
    field_map = [
        ("#square", "square"),
        ("#angle", "angle"),
        ("#apex_len", "apex_len"),
        ("#eaves_len", "eaves_len"),
        ("#fasciaboard_len", "fasciaboard_len"),
        ("#eaves_width", "eaves_width"),
        ("#ridge_len", "ridge_len"),
        ("#pediment_len", "pediment_len"),
        ("#junc_len", "junc_len"),
        ("#walls_thick", "walls_thick"),
    ]

    for selector, key in field_map:
        value = params.get(key)
        if value is None:
            continue

        exists = await page.evaluate(
            f"() => !!document.querySelector('{selector}')"
        )
        if not exists:
            log.info(f"5/6 поля {selector} нет для этого типа крыши — пропускаю")
            continue

        await _fill(page, selector, value)
        log.info(f"5/6 заполнено {selector} = {value}")

    # --- 5б. Дополнительные параметры (чекбоксы) ---
    # ВАЖНО: этот блок выполняется ОДИН РАЗ, ПОСЛЕ всех основных полей.
    # Он должен быть ВНЕ цикла field_map.

    log.info("5б/6 обрабатываю доп. параметры")

    async def _enable_checkbox(cb_id: str, subfield_selector: str | None = None) -> bool:
        """
        Включает чекбокс. Если указан subfield_selector — ждёт появления
        его подполей. Возвращает True, если всё сработало.
        """
        # Проверяем, может уже включён
        already = await page.evaluate(
            f"document.getElementById('{cb_id}')?.checked || false"
        )
        if not already:
            # Клик через JS — самый надёжный способ для Vue-чекбоксов
            await page.evaluate(f"document.getElementById('{cb_id}').click()")
            await page.wait_for_timeout(300)

        checked = await page.evaluate(
            f"document.getElementById('{cb_id}')?.checked || false"
        )
        log.info(f"    чекбокс {cb_id} checked = {checked}")

        if subfield_selector:
            try:
                await page.wait_for_selector(subfield_selector, timeout=5000)
                log.info(f"    подполе {subfield_selector} появилось")
                return True
            except Exception:
                log.warning(f"    подполе {subfield_selector} НЕ появилось")
                return False
        return True

    # Кирпичная труба
    if params.get("brickchimney"):
        log.info("  → кирпичная труба")
        ok = await _enable_checkbox("brickchimney", "#brickchimney_cnt")
        if ok:
            if params.get("brickchimney_cnt") is not None:
                await _fill(page, "#brickchimney_cnt", params["brickchimney_cnt"])
            if params.get("brickchimney_area") is not None:
                await _fill(page, "#brickchimney_area", params["brickchimney_area"])
            if params.get("brickchimney_perimeter") is not None:
                await _fill(page, "#brickchimney_perimeter", params["brickchimney_perimeter"])

    # Мансардное окно
    if params.get("dormerwindow"):
        log.info("  → мансардное окно")
        ok = await _enable_checkbox("dormerwindow", "#dormerwindow_area")
        if ok and params.get("dormerwindow_area") is not None:
            await _fill(page, "#dormerwindow_area", params["dormerwindow_area"])

    # Канализационный выход
    if params.get("sewerage"):
        log.info("  → канализация")
        ok = await _enable_checkbox("sewerage", "#sewerage_fan")
        if ok:
            if params.get("sewerage_fan") is not None:
                await _fill(page, "#sewerage_fan", params["sewerage_fan"])
            if params.get("yearound"):
                await _enable_checkbox("yearound")

    # Точечные аэраторы
    if params.get("aerators"):
        log.info("  → точечные аэраторы")
        ok = await _enable_checkbox("aerators", "#aerators_cnt")
        if ok and params.get("aerators_cnt") is not None:
            await _fill(page, "#aerators_cnt", params["aerators_cnt"])

    log.info("5б/6 OK")

    # --- 5в. Blur и ожидание пересчёта ---
    log.info("5в/6 blur")
    await page.evaluate("document.activeElement && document.activeElement.blur()")
    await page.wait_for_timeout(3000)

    # --- 6. Результат ---
    log.info("6/6 читаю результат")
    materials = await _read_result(page)
    log.info(f"6/6 OK, материалов: {len(materials)}")

    return {"ok": True, "materials": materials}

async def _fill(page: Page, selector: str, value) -> None:
    """Заполняет поле и триггерит change/input (калькулятор слушает их)."""
    await page.fill(selector, str(value))
    await page.dispatch_event(selector, "change")
    await page.dispatch_event(selector, "input")
    await page.wait_for_timeout(200)


async def _read_result(page: Page) -> List[Dict[str, str]]:
    """
    Собирает строки результата из блока «Материалы для кровли».
    Каждая строка — <li> с <p> внутри (название) и текстом количества.
    """
    raw = await page.evaluate(
        """() => {
        const out = [];
        const lis = document.querySelectorAll('.calc-result-left__list li');
        for (const li of lis) {
            const p = li.querySelector('p');
            if (!p) continue;
            const name = p.innerText.trim();

            const strong = li.querySelector('strong');
            let qty = strong ? strong.innerText.trim() : '';

            // Убираем название из общего текста, чтобы получить количество
            if (!qty) {
                const full = li.innerText.trim();
                qty = full.replace(name, '').trim();
            }
            if (!name) continue;
            out.push({ name, qty });
        }
        return out;
    }"""
    )

    # Чистим строки от лишних пробелов и переносов
    cleaned: List[Dict[str, str]] = []
    for item in raw:
        name = re.sub(r"\s+", " ", item["name"]).strip()
        qty = re.sub(r"\s+", " ", item["qty"]).strip()
        if not name or not qty:
            continue
        # Пропускаем возможный мусор
        if "Долговечность" in name:
            continue
        cleaned.append({"name": name, "qty": qty})

    return cleaned