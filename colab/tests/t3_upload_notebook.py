"""
T3: Faz upload de um notebook .ipynb no Colab via File > Upload notebook.
Usa Chrome real via subprocess + CDP (sem deteccao de automacao).
Esperado: notebook abre no editor Colab.

PRE-REQUISITO: T2 passou (login salvo em .colab-profile/).
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from chrome_helper import launch_chrome, wait_cdp_ready, CDP_URL

# Notebook minimo de teste
NOTEBOOK  = Path("/tmp/test_notebook.ipynb")
NOTEBOOK.write_text(json.dumps({
    "cells": [{
        "cell_type": "code",
        "source": ["print('Hello from Colab T3 test!')"],
        "metadata": {}, "outputs": [], "execution_count": None
    }],
    "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
    "nbformat": 4, "nbformat_minor": 4
}))
print(f"Notebook de teste criado: {NOTEBOOK}")


async def upload_notebook(page, notebook_path: Path) -> bool:
    print("Clicando no menu File...")
    for selector in [
        'colab-toolbar-button:has-text("File")',
        '[id*="file"]',
        'text=File',
    ]:
        try:
            await page.click(selector, timeout=5000)
            print(f"  File clicado via: {selector}")
            break
        except Exception:
            continue
    else:
        print("FALHA: nao encontrou menu File")
        buttons = await page.query_selector_all('colab-toolbar-button, [role="menuitem"], button')
        print("Botoes encontrados:")
        for b in buttons[:15]:
            t = await b.inner_text()
            if t.strip():
                print(f"  '{t.strip()}'")
        return False

    await asyncio.sleep(1)

    print("Clicando em Upload notebook...")
    for selector in [
        'text=Upload notebook',
        '[data-command="file_upload_notebook"]',
    ]:
        try:
            await page.click(selector, timeout=3000)
            print(f"  Upload notebook clicado via: {selector}")
            break
        except Exception:
            continue
    else:
        print("FALHA: nao encontrou 'Upload notebook'")
        items = await page.query_selector_all('[role="menuitem"]')
        print("Itens de menu encontrados:")
        for item in items:
            t = await item.inner_text()
            if t.strip():
                print(f"  '{t.strip()}'")
        return False

    await asyncio.sleep(2)

    file_input = await page.query_selector('input[type="file"]')
    if not file_input:
        for sel in ['text=Browse', 'text=Choose file', 'button:has-text("Browse")']:
            try:
                await page.click(sel, timeout=3000)
                file_input = await page.query_selector('input[type="file"]')
                if file_input:
                    break
            except Exception:
                continue

    if not file_input:
        print("FALHA: input[type='file'] nao encontrado")
        dialogs = await page.query_selector_all('[role="dialog"], mat-dialog-container')
        for d in dialogs:
            print(await d.inner_text())
        return False

    await file_input.set_input_files(str(notebook_path))
    print(f"Arquivo injetado: {notebook_path.name}")
    await asyncio.sleep(4)

    title = await page.title()
    print(f"Titulo da pagina apos upload: {title}")
    return True


async def main():
    proc = launch_chrome()
    wait_cdp_ready()

    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        ctx  = browser.contexts[0] if browser.contexts else None
        if not ctx:
            print("FALHA: nenhum contexto CDP encontrado")
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
            print("OK - Notebook carregado com sucesso!")
        else:
            print("FALHA - Verificar seletores acima")

        print("Aguardando 5s para verificacao visual...")
        await asyncio.sleep(5)

    proc.terminate()
    proc.wait()
    print("Chrome fechado.")


asyncio.run(main())
