"""
T6: Teste visual com headless=False — percorre o fluxo completo pausando em cada step.

Objetivo: permitir inspeção visual página a página do fluxo de automação Colab.
Em cada step, imprime diagnóstico DOM e aguarda N segundos antes de continuar.

Uso:
  python colab/tests/t6_visual_debug.py

PRE-REQUISITO: Login Google ativo no perfil .colab-profile (rodar T2 antes se necessario).
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from chrome_helper import launch_chrome, wait_cdp_ready, CDP_URL

ROOT         = Path(__file__).parent.parent.parent
DATASET_PATH = ROOT / "data" / "processed" / "training_data.jsonl"
MODELS_DIR   = ROOT / "models"

# Seletores verificados em cada step de diagnóstico
SELECTORS_TO_CHECK = [
    ('a[aria-label="Fazer login"]',         "Login button (PT-BR)"),
    ('a[aria-label="Sign in"]',             "Login button (EN)"),
    ('[aria-label*="Conta do Google"]',     "Google account"),
    ('[data-authuser]',                     "Auth user attr"),
    ('text=Arquivo',                        "Menu Arquivo (PT-BR)"),
    ('text=File',                           "Menu File (EN)"),
    ('.output-area input[type="file"]',     "Dataset file input"),
    ('input[type="file"]',                  "Any file input"),
]


async def step(name: str, page, wait: int = 5):
    """Imprime diagnóstico DOM e pausa para inspeção visual."""
    print(f"\n{'='*55}")
    print(f"STEP: {name}")
    print(f"URL:   {page.url}")
    print(f"Title: {await page.title()}")
    print("--- Seletores ---")
    for sel, label in SELECTORS_TO_CHECK:
        try:
            el = await page.query_selector(sel)
            status = "FOUND" if el else "NOT FOUND"
        except Exception as exc:
            status = f"ERROR ({exc})"
        print(f"  [{label}]: {status}")
    # Check for .gguf files in models/
    gguf_files = list(MODELS_DIR.glob("*.gguf")) if MODELS_DIR.exists() else []
    print(f"  [GGUF files in models/]: {[f.name for f in gguf_files] or 'none'}")
    print(f"Aguardando {wait}s para inspeção visual...")
    await asyncio.sleep(wait)


async def check_login(page) -> bool:
    """Verifica se o usuário está logado (2 checks consecutivos sem botão de login)."""
    confirmed = 0
    for _ in range(6):
        login_btn = await page.query_selector('a[aria-label="Fazer login"], a[aria-label="Sign in"]')
        if not login_btn:
            confirmed += 1
            if confirmed >= 2:
                return True
        else:
            confirmed = 0
        await asyncio.sleep(1)
    return False


async def main():
    print("T6: Teste visual — fluxo completo com headless=False")
    print(f"Dataset: {DATASET_PATH} ({'EXISTS' if DATASET_PATH.exists() else 'NOT FOUND'})")

    proc = launch_chrome()
    wait_cdp_ready(timeout_s=20)

    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        ctx     = browser.contexts[0]
        page    = ctx.pages[0] if ctx.pages else await ctx.new_page()

        # ── Step 1: Página inicial do Colab ────────────────────────
        await page.wait_for_load_state("domcontentloaded", timeout=30000)
        await step("1 — Colab carregado", page, wait=5)

        # ── Step 2: Verificar login ─────────────────────────────────
        print("\nVerificando login...")
        logged_in = await check_login(page)
        if logged_in:
            print("Login detectado — usuario autenticado.")
        else:
            print("NAO logado — fazer login manual e pressionar Enter para continuar...")
            input("Pressione Enter apos fazer login no Chrome...")
        await step("2 — Login verificado", page, wait=5)

        # ── Step 3: Abrir menu Arquivo ──────────────────────────────
        print("\nTentando abrir menu Arquivo/File...")
        for menu_text in ["Arquivo", "File"]:
            try:
                await page.click(f'text="{menu_text}"', timeout=3000)
                print(f"Menu '{menu_text}' clicado.")
                break
            except Exception:
                pass
        await step("3 — Menu Arquivo aberto", page, wait=5)

        # ── Step 4: Opção de upload de notebook ────────────────────
        for upload_text in ["Fazer upload de notebook", "Upload notebook"]:
            try:
                await page.click(f'text="{upload_text}"', timeout=3000)
                print(f"Opção '{upload_text}' clicada.")
                break
            except Exception:
                pass
        await step("4 — Dialog upload de notebook", page, wait=5)

        # Fechar dialog se abriu (sem notebook real aqui)
        for dismiss in ["Cancelar", "Cancel", "Fechar", "Close"]:
            try:
                await page.click(f'button:has-text("{dismiss}")', timeout=2000)
                print(f"Dialog fechado via '{dismiss}'")
                break
            except Exception:
                pass

        # ── Step 5: Menu Ambiente de execucao ──────────────────────
        for menu_text in ["Ambiente de execução", "Runtime"]:
            try:
                await page.click(f'text="{menu_text}"', timeout=3000)
                print(f"Menu '{menu_text}' clicado.")
                break
            except Exception:
                pass
        await step("5 — Menu Runtime aberto", page, wait=5)

        # ── Step 6: Alterar tipo de ambiente ───────────────────────
        for option_text in ["Alterar tipo de ambiente de execução", "Change runtime type"]:
            try:
                await page.click(f'text="{option_text}"', timeout=3000)
                print(f"Opção '{option_text}' clicada.")
                break
            except Exception:
                pass
        await step("6 — Dialog GPU aberto (verificar radio buttons T4)", page, wait=8)

        # Inspecionar radio buttons do dialog GPU
        print("\nInspecionando radio buttons no dialog GPU...")
        buttons = await page.get_by_role("button").all()
        print(f"  Total de botões na página: {len(buttons)}")
        radios = await page.query_selector_all('input[type="radio"]')
        print(f"  Radio buttons encontrados: {len(radios)}")
        for r in radios:
            val   = await r.get_attribute("value") or ""
            label = await r.get_attribute("aria-label") or ""
            print(f"    radio: value='{val}' aria-label='{label}'")

        # Fechar dialog GPU
        for dismiss in ["Cancelar", "Cancel"]:
            try:
                await page.click(f'button:has-text("{dismiss}")', timeout=2000)
                print(f"Dialog GPU fechado via '{dismiss}'")
                break
            except Exception:
                pass

        # ── Step 7: Verificar widget de upload de dataset ──────────
        print("\nVerificando widget de upload de dataset (output-area input[type='file'])...")
        file_input = await page.query_selector('.output-area input[type="file"]')
        if file_input:
            print("  Widget de upload de dataset ENCONTRADO!")
            if DATASET_PATH.exists():
                print(f"  Injetando dataset: {DATASET_PATH}")
                await file_input.set_input_files(str(DATASET_PATH))
                print("  set_input_files() executado.")
            else:
                print(f"  Dataset NAO encontrado em: {DATASET_PATH}")
        else:
            print("  Widget NOT FOUND — celulas ainda nao executaram ou notebook nao carregado.")
        await step("7 — Injecao de dataset testada", page, wait=8)

        # ── Step 8: Verificar modelos GGUF ─────────────────────────
        await step("8 — Verificar downloads GGUF", page, wait=5)

        print("\n" + "="*55)
        print("T6 concluido — Chrome permanece aberto para inspeção.")
        print("Pressione Ctrl+C ou feche o Chrome manualmente.")
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            pass

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    print("Chrome encerrado.")


asyncio.run(main())
