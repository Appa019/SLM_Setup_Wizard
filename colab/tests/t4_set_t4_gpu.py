"""
T4: Configura runtime T4 GPU via Runtime > Change runtime type.
Usa Chrome real via subprocess + CDP.
Esperado: dialog fecha, runtime confirmado como T4 GPU.

PRE-REQUISITO: T3 passou (notebook aberto no Colab).
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from chrome_helper import launch_chrome, wait_cdp_ready, CDP_URL

NOTEBOOK = Path("/tmp/test_notebook.ipynb")


async def set_t4_gpu(page) -> bool:
    print("Clicando no menu Runtime...")
    for selector in ['text=Runtime', 'colab-toolbar-button:has-text("Runtime")']:
        try:
            await page.click(selector, timeout=8000)
            print(f"  Runtime clicado via: {selector}")
            break
        except Exception:
            continue
    else:
        print("FALHA: nao encontrou menu Runtime")
        return False

    await asyncio.sleep(1)

    print("Clicando em Change runtime type...")
    for selector in [
        'text=Change runtime type',
        '[data-command*="runtime_type"]',
    ]:
        try:
            await page.click(selector, timeout=5000)
            print(f"  'Change runtime type' clicado via: {selector}")
            break
        except Exception:
            continue
    else:
        print("FALHA: nao encontrou 'Change runtime type'")
        items = await page.query_selector_all('[role="menuitem"]')
        print("Itens do menu Runtime:")
        for item in items:
            t = await item.inner_text()
            if t.strip():
                print(f"  '{t.strip()}'")
        return False

    await asyncio.sleep(2)

    print("Inspecionando dialog de runtime (selects disponiveis):")
    selects = await page.query_selector_all('select')
    for s in selects:
        name  = await s.get_attribute('name') or await s.get_attribute('id') or '?'
        value = await s.input_value()
        opts  = await s.evaluate('el => Array.from(el.options).map(o => o.value)')
        print(f"  select name='{name}' value='{value}' options={opts}")

    print("Selecionando GPU...")
    gpu_set = False
    for selector, value in [
        ('select[name="acceleratorType"]', 'GPU'),
        ('select[name="hardwareAccelerator"]', 'GPU'),
    ]:
        try:
            await page.select_option(selector, value, timeout=5000)
            print(f"  GPU selecionado via: {selector}")
            gpu_set = True
            break
        except Exception:
            continue

    if not gpu_set:
        for sel in ['text=GPU', '[value="GPU"]', 'mat-radio-button:has-text("GPU")']:
            try:
                await page.click(sel, timeout=3000)
                print(f"  GPU clicado via: {sel}")
                gpu_set = True
                break
            except Exception:
                continue

    if not gpu_set:
        print("FALHA: nao conseguiu selecionar GPU — verificar selects acima")
        return False

    await asyncio.sleep(1)

    # Subtipo T4 (se houver)
    for selector, value in [
        ('select[name="acceleratorSubType"]', 'T4'),
        ('select[name="gpuType"]', 'T4'),
    ]:
        try:
            await page.select_option(selector, value, timeout=3000)
            print(f"  T4 selecionado via: {selector}")
            break
        except Exception:
            pass

    print("Clicando Save...")
    for selector in [
        'button:has-text("Save")',
        'button:has-text("OK")',
        '.confirm-button',
    ]:
        try:
            await page.click(selector, timeout=5000)
            print(f"  Save clicado via: {selector}")
            break
        except Exception:
            continue
    else:
        print("FALHA: nao encontrou botao Save")
        buttons = await page.query_selector_all('button')
        print("Botoes no dialog:")
        for b in buttons:
            t = await b.inner_text()
            if t.strip():
                print(f"  '{t.strip()}'")
        return False

    await asyncio.sleep(2)
    print("OK - T4 GPU configurado!")
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
        await asyncio.sleep(3)

        # Upload notebook para ter algo aberto
        print("Abrindo notebook de teste...")
        try:
            await page.click('text=File', timeout=8000)
            await page.click('text=Upload notebook', timeout=5000)
            await asyncio.sleep(2)
            fi = await page.query_selector('input[type="file"]')
            if fi and NOTEBOOK.exists():
                await fi.set_input_files(str(NOTEBOOK))
                await asyncio.sleep(4)
        except Exception as e:
            print(f"Aviso no upload (pode continuar): {e}")

        ok = await set_t4_gpu(page)
        print("RESULTADO:", "OK" if ok else "FALHA")

        await asyncio.sleep(3)

    proc.terminate()
    proc.wait()
    print("Chrome fechado.")


asyncio.run(main())
