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
    print("\nVERIFICANDO STATUS DE LOGIN:")
    print("-" * 40)

    for i in range(timeout_s // 3):   # poll a cada 3s
        try:
            url   = page.url
            title = await page.title()
            elapsed = i * 3

            # Imprime status a cada 15s ou quando mudar
            if i % 5 == 0:
                print(f"  [{elapsed:>4}s] URL:   {url[:80]}")
                print(f"         titulo: {title[:60]}")

            # NAO logado: redirecionou para Google login
            if "accounts.google.com" in url:
                if i == 0:
                    print("  → Nao logado. Faca login no Chrome que abriu...")
                await asyncio.sleep(3)
                continue

            # LOGADO: esta no Colab e o titulo indica a UI carregou
            if "colab.research.google.com" in url:
                colab_title = (
                    "colaboratory" in title.lower()
                    or "colab" in title.lower()
                    or title == ""          # pagina inicial sem notebook
                )
                if colab_title and elapsed >= 3:
                    # Confirma que nao foi redirecionado de volta ao login
                    await asyncio.sleep(2)
                    if "accounts.google.com" not in page.url:
                        return True

        except Exception as e:
            err = str(e)
            if "destroyed" in err or "navigation" in err.lower() or "Target" in err:
                if i % 5 == 0:
                    print(f"  [{i*3:>4}s] Pagina navegando (SPA), aguardando...")
                await asyncio.sleep(1)
                continue
            print(f"  Erro inesperado: {e}")

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
