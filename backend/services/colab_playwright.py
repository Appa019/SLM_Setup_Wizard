import asyncio
import json
from pathlib import Path

training_state: dict = {
    "running": False,
    "step": "",
    "steps_done": [],
    "log": [],
    "metrics": {"epoch": 0, "loss": None, "step": 0},
    "finished": False,
    "error": "",
    "model_path": "",
}

STEPS = [
    "Abrindo Google Colab...",
    "Verificando login...",
    "Fazendo upload do notebook...",
    "Configurando runtime GPU...",
    "Iniciando execucao das celulas...",
    "Instalando dependencias...",
    "Carregando dataset...",
    "Carregando modelo base...",
    "Treinando (LoRA/QLoRA)...",
    "Convertendo para GGUF...",
    "Baixando modelo...",
]


def get_training_state() -> dict:
    return dict(training_state)


def _log(msg: str):
    training_state["log"] = (training_state["log"] + [msg])[-50:]  # Keep last 50


async def run_colab_automation(notebook_path: Path, dataset_path: Path, model_out_dir: Path):
    """
    Automates Google Colab via Playwright (visible browser).
    The browser stays visible so the user can monitor and intervene.
    """
    global training_state
    training_state.update({
        "running": True, "step": STEPS[0], "steps_done": [], "log": [],
        "metrics": {"epoch": 0, "loss": None, "step": 0},
        "finished": False, "error": "", "model_path": "",
    })

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            _log("Iniciando browser Chromium...")
            browser = await p.chromium.launch(
                headless=False,
                args=["--start-maximized"],
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                accept_downloads=True,
            )
            page = await context.new_page()

            # Step 1: Open Colab
            _update_step(STEPS[0])
            _log("Abrindo colab.research.google.com...")
            await page.goto("https://colab.research.google.com", timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=15000)

            # Step 2: Check login
            _update_step(STEPS[1])
            _log("Verificando se usuario esta logado...")
            await asyncio.sleep(3)

            # Check if logged in by looking for sign-in button
            sign_in = await page.query_selector('a[href*="accounts.google.com"]')
            if sign_in:
                _log("Usuario nao esta logado. Aguardando login manual (60s)...")
                training_state["step"] = "Aguardando login manual no browser..."
                await asyncio.sleep(60)

            # Step 3: Upload notebook
            _update_step(STEPS[2])
            _log(f"Fazendo upload do notebook: {notebook_path.name}")

            # Click "File > Upload notebook"
            try:
                await page.keyboard.press("Escape")
                await asyncio.sleep(1)

                # Use file input for upload
                file_input = await page.query_selector('input[type="file"]')
                if not file_input:
                    # Try opening via URL
                    await page.goto(
                        f"https://colab.research.google.com/drive/",
                        timeout=15000
                    )
                    await asyncio.sleep(2)

                # Navigate to upload URL directly
                await page.goto("https://colab.research.google.com/#create=true", timeout=15000)
                await asyncio.sleep(3)

                _log("Notebook aberto no Colab")
            except Exception as e:
                _log(f"Aviso ao navegar: {e}")

            # Step 4: Select GPU runtime
            _update_step(STEPS[3])
            _log("Configurando runtime GPU T4...")
            try:
                # Runtime > Change runtime type
                await page.click("text=Runtime", timeout=5000)
                await asyncio.sleep(0.5)
                await page.click("text=Change runtime type", timeout=5000)
                await asyncio.sleep(1)
                # Select T4 GPU
                gpu_option = await page.query_selector('text=T4 GPU')
                if gpu_option:
                    await gpu_option.click()
                await page.keyboard.press("Enter")
                await asyncio.sleep(2)
                _log("Runtime GPU configurado")
            except Exception as e:
                _log(f"Aviso ao configurar runtime: {e}. Continue manualmente se necessario.")

            # Notify user about manual steps
            _log("=" * 40)
            _log("ACAO NECESSARIA: No browser aberto:")
            _log("1. Faca upload do notebook gerado (colab/generated_notebook.ipynb)")
            _log("2. Execute as celulas sequencialmente (Ctrl+F9 para executar tudo)")
            _log("3. Na celula de upload, faca upload do training_data.jsonl")
            _log("4. Aguarde o treinamento concluir e faca download do modelo_final.gguf")
            _log("=" * 40)

            # Step 5: Monitor (wait for user to run cells)
            _update_step(STEPS[4])

            # Simulate monitoring while browser stays open
            for i in range(180):  # Wait up to 30 minutes
                await asyncio.sleep(10)
                _log(f"Aguardando execucao... {(i+1)*10}s")
                training_state["metrics"]["step"] = (i + 1) * 10

                # Check if model file was downloaded
                gguf_files = list(model_out_dir.glob("*.gguf"))
                if gguf_files:
                    _log(f"Modelo GGUF detectado: {gguf_files[0].name}")
                    training_state["model_path"] = str(gguf_files[0])
                    break

            await browser.close()

    except ImportError:
        training_state["error"] = "Playwright nao instalado. Execute: playwright install chromium"
        _log(training_state["error"])
    except Exception as e:
        training_state["error"] = str(e)
        _log(f"Erro: {e}")

    training_state["running"] = False
    training_state["finished"] = True
    _log("Automacao Colab finalizada")


def _update_step(step: str):
    training_state["step"] = step
    training_state["steps_done"].append(step)
    _log(step)
