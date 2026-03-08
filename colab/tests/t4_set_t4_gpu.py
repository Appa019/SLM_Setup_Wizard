"""
T4: Configura runtime T4 GPU via Ambiente de execução > Alterar o tipo de ambiente.
UI em portugues:
  - Menu: 'Ambiente de execução'
  - Item: 'Alterar o tipo de ambiente de execução'
  - Botao save: 'Salvar'

PRE-REQUISITO: T3 passou (notebook aberto no Colab).
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from chrome_helper import launch_chrome, wait_cdp_ready, CDP_URL

NOTEBOOK = Path("/tmp/test_notebook.ipynb")


async def set_gpu(page) -> bool:
    print("Clicando em 'Ambiente de execução'...")
    for selector in [
        'text=Ambiente de execução',
        'text=Runtime',
    ]:
        try:
            await page.click(selector, timeout=8000)
            print(f"  Clicado via: '{selector}'")
            break
        except Exception:
            continue
    else:
        print("FALHA: menu de runtime nao encontrado")
        return False

    await asyncio.sleep(1)

    print("Clicando em 'Alterar o tipo de ambiente de execução'...")
    for selector in [
        'text=Alterar o tipo de ambiente de execução',
        'text=Change runtime type',
        '[data-command*="runtime_type"]',
    ]:
        try:
            await page.click(selector, timeout=5000)
            print(f"  Clicado via: '{selector}'")
            break
        except Exception:
            continue
    else:
        print("FALHA: item nao encontrado. Itens do menu:")
        items = await page.query_selector_all('[role="menuitem"]')
        for item in items:
            try:
                t = (await item.inner_text()).strip()
                if t: print(f"  '{t}'")
            except Exception:
                pass
        return False

    await asyncio.sleep(2)

    # Inspecionar selects no dialog
    print("\nSelects no dialog:")
    selects = await page.query_selector_all('select')
    for s in selects:
        name  = await s.get_attribute('name') or await s.get_attribute('id') or '?'
        value = await s.input_value()
        opts  = await s.evaluate('el => Array.from(el.options).map(o => ({v:o.value, t:o.text}))')
        print(f"  select '{name}' = '{value}' opcoes={opts}")

    # Selecionar GPU
    print("\nSelecionando GPU...")
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
        # Tentar via radio/click
        for sel in [
            '[value="GPU"]',
            'text=GPU',
            'mat-radio-button:has-text("GPU")',
        ]:
            try:
                await page.click(sel, timeout=3000)
                print(f"  GPU clicado via: {sel}")
                gpu_set = True
                break
            except Exception:
                continue

    if not gpu_set:
        print("FALHA: nao conseguiu selecionar GPU")
        # Debug: listar todos os inputs/radios do dialog
        inputs = await page.query_selector_all('input, [role="radio"], select')
        print("Inputs no dialog:")
        for inp in inputs:
            t    = await inp.get_attribute('type') or '?'
            v    = await inp.get_attribute('value') or '?'
            lbl  = await inp.get_attribute('aria-label') or ''
            name = await inp.get_attribute('name') or ''
            print(f"  type={t} value={v} name={name} aria='{lbl}'")
        return False

    await asyncio.sleep(1)

    # Subtipo T4 (pode nao existir)
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

    # Salvar — botoes estao em shadow DOM (web components Material Design)
    # get_by_role encontra os 2 botoes do dialog: [0]=Cancelar [1]=Salvar
    print("\nClicando Salvar (shadow DOM)...")
    saved = False

    # Tentativa 1: via JavaScript percorrendo shadow roots
    clicked_via_js = await page.evaluate("""
    () => {
        const scan = (root) => {
            for (const el of root.querySelectorAll('*')) {
                const t = (el.innerText || el.textContent || '').trim();
                if (t === 'Salvar' || t === 'Save') { el.click(); return true; }
                if (el.shadowRoot && scan(el.shadowRoot)) return true;
            }
            return false;
        };
        return scan(document);
    }
    """)
    if clicked_via_js:
        print("  Salvar clicado via JS (shadow DOM)")
        saved = True

    # Tentativa 2: segundo botao via get_by_role
    if not saved:
        try:
            btns = await page.get_by_role("button").all()
            if len(btns) >= 2:
                await btns[-1].click()
                print(f"  Salvar clicado via get_by_role (ultimo botao, total={len(btns)})")
                saved = True
        except Exception as e:
            print(f"  get_by_role falhou: {e}")

    # Tentativa 3: Enter confirma o dialog
    if not saved:
        await page.keyboard.press("Enter")
        print("  Enter pressionado para confirmar dialog")
        saved = True

    if not saved:
        return False

    await asyncio.sleep(2)
    print("OK - GPU configurado!")
    return True


async def upload_notebook_quick(page, notebook_path):
    """Upload rapido para ter notebook aberto."""
    await page.keyboard.press("Escape")
    await asyncio.sleep(1)
    try:
        await page.click('text=Arquivo', timeout=5000)
        await page.click('text=Fazer upload de notebook', timeout=4000)
        await asyncio.sleep(2)
        fi = await page.query_selector('input[type="file"]')
        if fi and notebook_path.exists():
            await fi.set_input_files(str(notebook_path))
            await asyncio.sleep(4)
            print("  Notebook aberto")
    except Exception as e:
        print(f"  Aviso no upload: {e}")


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

        await upload_notebook_quick(page, NOTEBOOK)
        ok = await set_gpu(page)
        print("\nRESULTADO:", "OK" if ok else "FALHA")

        await asyncio.sleep(3)

    proc.terminate()
    proc.wait()
    print("Chrome fechado.")


asyncio.run(main())
