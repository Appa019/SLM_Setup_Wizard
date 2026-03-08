"""
T1: Verifica que o Chrome real do sistema abre via Playwright channel='chrome'.
Esperado: Chrome abre visualmente, navega para example.com, imprime titulo, fecha.
"""
import asyncio
from pathlib import Path

ROOT    = Path(__file__).parent.parent.parent
PROFILE = ROOT / ".colab-profile"


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        print(f"Abrindo Chrome real (channel='chrome')...")
        print(f"Perfil persistente: {PROFILE}")
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE),
            channel="chrome",
            headless=False,
            args=["--start-maximized"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto("https://example.com")
        title = await page.title()
        print(f"Titulo da pagina: {title}")
        assert "Example" in title, f"Titulo inesperado: {title}"
        await asyncio.sleep(2)
        await ctx.close()
        print("OK - Chrome abriu, navegou e fechou corretamente")


asyncio.run(main())
