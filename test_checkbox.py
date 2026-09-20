"""
Диагностика: какие подполя появляются после клика по чекбоксу 'кирпичная труба'.
"""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            locale="ru-RU",
        )
        page = await context.new_page()

        print("1. Открываю tn.ru...")
        await page.goto(
            "https://www.tn.ru/calculators/shinglas/",
            wait_until="domcontentloaded",
        )
        await page.wait_for_selector(".quiz__slide", timeout=60000)

        print("2. Выбираю: односкатная → ультра фристайл → галька")
        await page.click(".quiz__slide:has-text('Односкатная')")
        await page.wait_for_timeout(1500)
        await page.click(".main-collection-in__link:has-text('Ультра Фристайл')")
        await page.wait_for_timeout(1500)
        await page.click(".additional_palette_block:has-text('Галька')")
        await page.wait_for_timeout(1500)

        print("\n3. Проверяю чекбоксы в форме:")
        for cb in ["brickchimney", "sewerage", "dormerwindow", "aerators"]:
            info = await page.evaluate(f'''() => {{
                const el = document.getElementById('{cb}');
                if (!el) return null;
                return {{
                    exists: true,
                    type: el.type,
                    checked: el.checked,
                    visible: el.offsetParent !== null,
                }};
            }}''')
            print(f"  {cb}: {info}")

        print("\n4. Кликаю по 'brickchimney' через JS...")
        await page.evaluate("document.getElementById('brickchimney').click()")
        await page.wait_for_timeout(1500)

        print("\n5. Какие INPUT'ы появились в форме после клика:")
        inputs = await page.evaluate('''() => {
            const form = document.querySelector('.tn-calculatorshinglas-calc');
            if (!form) return ['форма не найдена'];
            const all = form.querySelectorAll('input');
            return Array.from(all).map(el => ({
                id: el.id,
                name: el.name,
                type: el.type,
                value: el.value,
                visible: el.offsetParent !== null,
                placeholder: el.placeholder,
            }));
        }''')
        for inp in inputs:
            print(" ", inp)

        print("\n6. Все label'ы в форме:")
        labels = await page.evaluate('''() => {
            const form = document.querySelector('.tn-calculatorshinglas-calc');
            if (!form) return [];
            const all = form.querySelectorAll('label');
            return Array.from(all).map(el => ({
                for: el.getAttribute('for'),
                text: el.innerText.trim(),
            })).filter(l => l.for || l.text);
        }''')
        for lb in labels:
            print(" ", lb)

        input("\nНажми Enter, чтобы закрыть...")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())