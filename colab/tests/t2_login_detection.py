"""
T2: Detecta login no Colab via URL + titulo da pagina (mais robusto que seletores DOM).
- Logado:  URL fica em colab.research.google.com, titulo contem "Colaboratory"
- N logado: URL redireciona para accounts.google.com

Usa Chrome real via subprocess + CDP (Google nao bloqueia login).
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from chrome_helper import launch_chrome, wait_cdp_ready, CDP_URL


async def wait_for_login(page, timeout_s: int = 300) -> bool:
    """
    Logado = botao 'Fazer login' / 'Sign in' NAO existe na pagina.
    O seletor correto: a[aria-label="Fazer login"] (PT) ou a[aria-label="Sign in"] (EN).
    """
    print("\nVERIFICANDO STATUS DE LOGIN:")
    print("-" * 40)

    for i in range(timeout_s // 3):
        try:
            elapsed = i * 3

            # Aguardar pagina do Colab
            url = page.url
            if "accounts.google.com" in url:
                if i == 0 or i % 10 == 0:
                    print(f"  [{elapsed:>4}s] Pagina de login do Google aberta — faca login no Chrome...")
                await asyncio.sleep(3)
                continue

            if "colab.research.google.com" not in url:
                await asyncio.sleep(3)
                continue

            # Chave: verificar AUSENCIA do botao "Fazer login"
            sign_in_btn = await page.query_selector(
                'a[aria-label="Fazer login"], '
                'a[aria-label="Sign in"], '
                'a[aria-label="Sign In"]'
            )

            if i % 5 == 0:
                status = "NAO LOGADO" if sign_in_btn else "LOGADO"
                print(f"  [{elapsed:>4}s] {status} (botao login: {'encontrado' if sign_in_btn else 'ausente'})")

            if sign_in_btn:
                if i == 0:
                    print("  → Faca login no Chrome que abriu...")
                await asyncio.sleep(3)
                continue

            # Nao tem botao de login = esta logado
            return True

        except Exception as e:
            err = str(e)
            if "destroyed" in err or "navigation" in err.lower() or "Target" in err:
                if i % 5 == 0:
                    print(f"  [{i*3:>4}s] Pagina navegando (SPA)...")
                await asyncio.sleep(1)
                continue
            print(f"  Erro: {e}")

        await asyncio.sleep(3)

    return False


async def main():
    proc = launch_chrome()
    wait_cdp_ready()

    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        ctx = browser.contexts[0] if browser.contexts else None
        if not ctx:
            print("FALHA: nenhum contexto CDP")
            proc.terminate()
            return

        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        # Aguarda carregamento inicial
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass
        await asyncio.sleep(2)

        print(f"Conectado ao Chrome. URL inicial: {page.url}")

        logged = await wait_for_login(page, timeout_s=300)

        print("-" * 40)
        if logged:
            print("Login confirmado! Sessao salva em .colab-profile/")
            print("Proximas execucoes nao precisarao de login manual.")
        else:
            print("FALHA: login nao detectado em 5 min")
            print(f"URL final: {page.url}")
            print(f"Titulo final: {await page.title()}")

        await asyncio.sleep(2)

    proc.terminate()
    proc.wait()
    print("Chrome fechado.")


asyncio.run(main())
