"""
T3: Faz upload de um notebook .ipynb no Colab.
Fluxo:
  1. Abrir Colab
  2. ESC para fechar qualquer dialog de boas-vindas
  3. Arquivo > Fazer upload de notebook > injetar arquivo

UI em portugues: menu = 'Arquivo', item = 'Fazer upload de notebook'

PRE-REQUISITO: T2 passou (login salvo em .colab-profile/).
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from chrome_helper import launch_chrome, wait_cdp_ready, CDP_URL

NOTEBOOK = Path("/tmp/test_notebook.ipynb")
NOTEBOOK.write_text(json.dumps({
    "cells": [{
        "cell_type": "code",
        "source": ["print('Hello from Colab T3 test!')"],
        "metadata": {}, "outputs": [], "execution_count": None
    }],
    "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
    "nbformat": 4, "nbformat_minor": 4
}))
print(f"Notebook criado: {NOTEBOOK}")


async def upload_notebook(page, notebook_path: Path) -> bool:
    # ESC para fechar qualquer overlay/dialog inicial
    print("Pressionando ESC para fechar dialog inicial...")
    await page.keyboard.press("Escape")
    await asyncio.sleep(1)

    # Aguardar o menu Arquivo estar disponivel
    print("Aguardando menu Arquivo...")
    for attempt in range(5):
        try:
            await page.wait_for_selector(
                'text=Arquivo, text=File',
                timeout=5000
            )
            break
        except Exception:
            print(f"  tentativa {attempt+1}/5 — aguardando editor...")
            await asyncio.sleep(2)

    print("Clicando em Arquivo (File)...")
    clicked_file = False
    for selector in ['text=Arquivo', 'text=File']:
        try:
            await page.click(selector, timeout=5000)
            print(f"  Arquivo clicado via: '{selector}'")
            clicked_file = True
            break
        except Exception:
            continue

    if not clicked_file:
        print("FALHA: menu Arquivo nao encontrado")
        # Debug: listar textos curtos visiveis
        all_els = await page.query_selector_all('button, [role="menuitem"], [role="button"]')
        print(f"Elementos clicaveis ({len(all_els)}):")
        seen = set()
        for el in all_els[:40]:
            try:
                t = (await el.inner_text()).strip().split('\n')[0]
                if t and t not in seen:
                    seen.add(t)
                    print(f"  '{t}'")
            except Exception:
                pass
        return False

    await asyncio.sleep(1)

    print("Clicando em 'Fazer upload de notebook'...")
    clicked_upload = False
    for selector in [
        'text=Fazer upload de notebook',
        'text=Upload notebook',
        '[data-command="file_upload_notebook"]',
    ]:
        try:
            await page.click(selector, timeout=4000)
            print(f"  Upload clicado via: '{selector}'")
            clicked_upload = True
            break
        except Exception:
            continue

    if not clicked_upload:
        print("FALHA: 'Fazer upload de notebook' nao encontrado")
        items = await page.query_selector_all('[role="menuitem"]')
        print(f"Itens do menu ({len(items)}):")
        for item in items:
            try:
                t = (await item.inner_text()).strip()
                if t:
                    print(f"  '{t}'")
            except Exception:
                pass
        return False

    await asyncio.sleep(2)

    # Injetar arquivo no input[type="file"]
    file_input = await page.query_selector('input[type="file"]')
    if not file_input:
        print("FALHA: input[type='file'] nao encontrado")
        return False

    await file_input.set_input_files(str(notebook_path))
    print(f"  Arquivo injetado: {notebook_path.name}")
    await asyncio.sleep(4)

    title = await page.title()
    print(f"Titulo apos upload: {title}")
    return True


async def main():
    proc = launch_chrome()
    wait_cdp_ready()

    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        ctx  = browser.contexts[0] if browser.contexts else None
        if not ctx:
            print("FALHA: nenhum contexto CDP")
            proc.terminate()
            return

        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        print("Navegando para o Colab...")
        await page.goto("https://colab.research.google.com", timeout=30000)
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        await asyncio.sleep(4)

        ok = await upload_notebook(page, NOTEBOOK)
        if ok:
            print("\nOK - Notebook carregado!")
        else:
            print("\nFALHA - Ver mensagens acima")

        print("Aguardando 5s para verificacao visual...")
        await asyncio.sleep(5)

    proc.terminate()
    proc.wait()
    print("Chrome fechado.")


asyncio.run(main())
