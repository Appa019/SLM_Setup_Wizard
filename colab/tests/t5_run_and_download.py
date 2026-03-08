"""
T5: Executa todas as celulas e intercepta o download automatico.
Usa notebook minimo: cria 'test_model.gguf' fake e chama files.download().
Esperado: arquivo salvo em /tmp/colab_dl/

IMPORTANTE: O Colab precisa conectar ao runtime (1-2 min antes de executar).

PRE-REQUISITO: T4 passou (T4 GPU configuravel, login ativo).
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from chrome_helper import launch_chrome, wait_cdp_ready, CDP_URL

# Notebook que cria um .gguf fake e faz download
NOTEBOOK = Path("/tmp/test_download.ipynb")
NOTEBOOK.write_text(json.dumps({
    "cells": [{
        "cell_type": "code",
        "source": [
            "from google.colab import files\n",
            "with open('test_model.gguf', 'w') as f:\n",
            "    f.write('fake gguf for playwright test')\n",
            "print('Arquivo criado')\n",
            "files.download('test_model.gguf')"
        ],
        "metadata": {}, "outputs": [], "execution_count": None
    }],
    "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
    "nbformat": 4, "nbformat_minor": 4
}))
print(f"Notebook de download criado: {NOTEBOOK}")

SAVE_DIR = Path("/tmp/colab_dl")
SAVE_DIR.mkdir(exist_ok=True)


async def main():
    downloaded_file = None
    download_event  = asyncio.Event()

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

        # Configurar Chrome para salvar downloads direto em SAVE_DIR via CDP
        cdp = await ctx.new_cdp_session(page)
        await cdp.send("Browser.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": str(SAVE_DIR),
        })
        print(f"Downloads configurados para: {SAVE_DIR}")

        # Registrar handler de download ANTES de qualquer acao
        # Nao chamar save_as() — Chrome ja salva em SAVE_DIR via setDownloadBehavior
        async def on_download(download):
            nonlocal downloaded_file
            fname     = download.suggested_filename
            save_path = SAVE_DIR / fname
            print(f"  -> Download iniciado: {fname}")
            # Aguardar Chrome terminar de escrever o arquivo
            for _ in range(20):
                if save_path.exists() and save_path.stat().st_size > 0:
                    break
                await asyncio.sleep(0.5)
            downloaded_file = str(save_path)
            size = save_path.stat().st_size if save_path.exists() else 0
            print(f"  -> Salvo em: {save_path} ({size} bytes)")
            download_event.set()

        page.on("download", on_download)

        print("Navegando para o Colab...")
        await page.goto("https://colab.research.google.com", timeout=30000)
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        await asyncio.sleep(3)

        # Upload do notebook de teste
        print("Fazendo upload do notebook de download...")
        await page.keyboard.press("Escape")
        await asyncio.sleep(1)
        try:
            await page.click('text=Arquivo', timeout=5000)
            await page.click('text=Fazer upload de notebook', timeout=4000)
            await asyncio.sleep(2)
            fi = await page.query_selector('input[type="file"]')
            if fi:
                await fi.set_input_files(str(NOTEBOOK))
            else:
                print("FALHA: input[type='file'] nao encontrado")
                proc.terminate()
                return
            await asyncio.sleep(4)
        except Exception as e:
            print(f"Erro no upload: {e}")
            proc.terminate()
            return

        # Run all via Ctrl+F9 (Executar tudo)
        print("Executando todas as celulas (Ctrl+F9)...")
        await page.keyboard.press("Control+F9")
        await asyncio.sleep(2)

        # Confirmar dialogs que possam aparecer
        for btn_text in ["Run anyway", "Executar assim mesmo", "Yes", "Sim", "OK"]:
            try:
                await page.click(f'button:has-text("{btn_text}")', timeout=2000)
                print(f"  Dialog confirmado: '{btn_text}'")
                break
            except Exception:
                pass

        # Tambem tentar via JS no shadow DOM
        await page.evaluate("""
        () => {
            const keywords = ['run anyway', 'executar assim', 'yes', 'sim'];
            const scan = (root) => {
                for (const el of root.querySelectorAll('*')) {
                    const t = (el.innerText || el.textContent || '').trim().toLowerCase();
                    if (keywords.some(k => t === k)) { el.click(); return true; }
                    if (el.shadowRoot && scan(el.shadowRoot)) return true;
                }
                return false;
            };
            return scan(document);
        }
        """)

        # Aguardar download (max 3 minutos para este teste simples)
        print("Aguardando execucao e download...")
        print("(O Colab precisa conectar ao runtime — pode levar 1-2 min)")
        try:
            await asyncio.wait_for(download_event.wait(), timeout=180)
            print(f"\nSUCESSO: arquivo salvo em {downloaded_file}")
            content = Path(downloaded_file).read_text()
            assert "fake gguf" in content, f"Conteudo inesperado: {content}"
            print("Conteudo verificado OK")
        except asyncio.TimeoutError:
            print("\nTIMEOUT: download nao ocorreu em 3 minutos")
            print("Verificar no Chrome:")
            print("  - Status do runtime (canto superior direito)")
            print("  - Output das celulas (pode ter erro)")

        await asyncio.sleep(3)

    proc.terminate()
    proc.wait()
    print("Chrome fechado.")


asyncio.run(main())
