import asyncio
import subprocess
import time
import urllib.request
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

# Caminhos comuns do Chrome no Linux
_CHROME_BINS = [
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
    "/opt/google/chrome/chrome",
    "/snap/bin/chromium",
]
_CDP_PORT = 9222
_CDP_URL  = f"http://localhost:{_CDP_PORT}"


def get_training_state() -> dict:
    return dict(training_state)


def _log(msg: str):
    training_state["log"] = (training_state["log"] + [msg])[-50:]


def _update_step(step: str):
    training_state["step"] = step
    training_state["steps_done"].append(step)
    _log(step)


def _find_chrome() -> str:
    for path in _CHROME_BINS:
        if Path(path).exists():
            return path
    raise RuntimeError(
        "Chrome nao encontrado. Instale com: sudo apt install google-chrome-stable"
    )


def _launch_chrome(profile_dir: Path) -> subprocess.Popen:
    chrome = _find_chrome()
    _log(f"Chrome: {chrome}")
    proc = subprocess.Popen(
        [
            chrome,
            f"--remote-debugging-port={_CDP_PORT}",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--start-maximized",
            "https://colab.research.google.com",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _log(f"Chrome iniciado (PID {proc.pid})")
    return proc


def _wait_cdp(timeout_s: int = 20):
    for _ in range(timeout_s * 2):
        try:
            urllib.request.urlopen(f"{_CDP_URL}/json", timeout=1)
            return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("CDP nao respondeu — Chrome nao iniciou corretamente")


async def run_colab_automation(notebook_path: Path, dataset_path: Path, model_out_dir: Path):
    """
    Automacao completa do Google Colab usando Chrome real via subprocess + CDP.

    Chrome e lancado SEM flags de automacao (Google nao bloqueia login).
    Playwright conecta via CDP apos o Chrome estar rodando.

    Perfil persistente em .colab-profile/ salva o login entre sessoes.

    Fluxo:
      1. Lanca Chrome (subprocess) → navega para Colab
      2. Detecta login (ausencia do botao 'Fazer login') — aguarda ate 5 min
      3. ESC para fechar dialog inicial
      4. Arquivo > Fazer upload de notebook → injeta notebook_path
      5. Ambiente de execucao > Alterar tipo → seleciona GPUs: T4 → Salvar
      6. Ctrl+F9 → Run all → confirma dialogs
      7. Intercepta download .gguf via page.on("download") → salva em model_out_dir
      8. Fecha Chrome
    """
    global training_state
    training_state.update({
        "running": True, "step": STEPS[0], "steps_done": [], "log": [],
        "metrics": {"epoch": 0, "loss": None, "step": 0},
        "finished": False, "error": "", "model_path": "",
    })

    PROJECT_ROOT = Path(__file__).parent.parent.parent
    PROFILE_DIR  = PROJECT_ROOT / ".colab-profile"
    model_out_dir.mkdir(parents=True, exist_ok=True)

    download_event = asyncio.Event()
    downloaded_path: list[str] = []
    proc = None

    try:
        from playwright.async_api import async_playwright

        # ── 1. Lançar Chrome ──────────────────────────────────────
        _update_step(STEPS[0])
        _log("Lancando Chrome com perfil persistente em .colab-profile/")
        _log("(Login sera salvo automaticamente apos a primeira vez)")
        proc = _launch_chrome(PROFILE_DIR)
        _wait_cdp()
        _log("CDP pronto — conectando Playwright...")

        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(_CDP_URL)
            ctx  = browser.contexts[0]
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()

            # Configurar download antes de qualquer acao
            cdp_session = await ctx.new_cdp_session(page)
            await cdp_session.send("Browser.setDownloadBehavior", {
                "behavior": "allow",
                "downloadPath": str(model_out_dir),
            })

            # Handler de download — registrado antes de Run all
            async def on_download(download):
                fname     = download.suggested_filename
                save_path = model_out_dir / fname
                _log(f"Download iniciado: {fname}")
                for _ in range(30):
                    if save_path.exists() and save_path.stat().st_size > 0:
                        break
                    await asyncio.sleep(0.5)
                _log(f"Download concluido: {fname}")
                downloaded_path.append(str(save_path))
                download_event.set()

            page.on("download", on_download)

            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            await asyncio.sleep(3)

            # ── 2. Detectar login ─────────────────────────────────
            _update_step(STEPS[1])
            logged_in = False
            for i in range(100):  # ate 5 min (100 × 3s)
                try:
                    url = page.url
                    if "accounts.google.com" in url:
                        if i == 0:
                            _log("Pagina de login do Google aberta — faca login no Chrome")
                        training_state["metrics"]["step"] = i * 3
                        await asyncio.sleep(3)
                        continue
                    sign_in = await page.query_selector(
                        'a[aria-label="Fazer login"],a[aria-label="Sign in"]'
                    )
                    if sign_in:
                        if i == 0:
                            _log("Botao 'Fazer login' visivel — faca login no Chrome")
                        elif i % 10 == 0:
                            _log(f"Aguardando login... {i * 3}s")
                        training_state["metrics"]["step"] = i * 3
                        await asyncio.sleep(3)
                        continue
                    logged_in = True
                    break
                except Exception as e:
                    if "destroyed" in str(e) or "navigation" in str(e).lower():
                        await asyncio.sleep(1)
                        continue

            if not logged_in:
                raise Exception("Login nao detectado em 5 minutos")
            _log("Login confirmado!")

            # ── 3. Upload do notebook ─────────────────────────────
            _update_step(STEPS[2])
            _log(f"Fazendo upload: {notebook_path.name}")
            await page.keyboard.press("Escape")
            await asyncio.sleep(1)

            clicked_file = False
            for sel in ['text=Arquivo', 'text=File']:
                try:
                    await page.click(sel, timeout=8000)
                    clicked_file = True
                    break
                except Exception:
                    continue
            if not clicked_file:
                raise Exception("Menu Arquivo nao encontrado")

            clicked_upload = False
            for sel in ['text=Fazer upload de notebook', 'text=Upload notebook']:
                try:
                    await page.click(sel, timeout=5000)
                    clicked_upload = True
                    break
                except Exception:
                    continue
            if not clicked_upload:
                raise Exception("Item 'Fazer upload de notebook' nao encontrado")

            await asyncio.sleep(2)
            file_input = await page.query_selector('input[type="file"]')
            if not file_input:
                raise Exception("Input de upload nao encontrado")

            await file_input.set_input_files(str(notebook_path))
            _log("Notebook injetado, aguardando carregar...")
            await asyncio.sleep(8)
            _log("Notebook carregado")

            # ── 4. Configurar T4 GPU ──────────────────────────────
            _update_step(STEPS[3])
            _log("Configurando runtime T4 GPU...")

            clicked_runtime = False
            for sel in ['text=Ambiente de execução', 'text=Runtime']:
                try:
                    await page.click(sel, timeout=10000)
                    clicked_runtime = True
                    break
                except Exception:
                    continue
            if not clicked_runtime:
                raise Exception("Menu Ambiente de execucao nao encontrado")

            await asyncio.sleep(1)

            clicked_change = False
            for sel in ['text=Alterar o tipo de ambiente de execução',
                        'text=Change runtime type']:
                try:
                    await page.click(sel, timeout=6000)
                    clicked_change = True
                    break
                except Exception:
                    continue
            if not clicked_change:
                raise Exception("Item 'Alterar tipo de ambiente' nao encontrado")

            await asyncio.sleep(3)

            # Selecionar GPUs: T4 (page.click simula clique real de mouse)
            for sel in ['text=GPUs: T4', '[role="radio"]:has-text("T4")']:
                try:
                    await page.click(sel, timeout=4000)
                    _log("GPUs: T4 selecionado")
                    break
                except Exception:
                    continue

            await asyncio.sleep(1)

            # Salvar — ultimo botao do dialog (Cancelar | Salvar)
            btns = await page.get_by_role("button").all()
            if btns:
                await btns[-1].click()
                _log("Salvar clicado")
            else:
                await page.keyboard.press("Enter")
                _log("Salvar via Enter")

            await asyncio.sleep(3)
            _log("Runtime T4 GPU configurado")

            # ── 5. Run all ────────────────────────────────────────
            _update_step(STEPS[4])
            _log("Iniciando execucao (Ctrl+F9)...")
            await page.keyboard.press("Control+F9")
            await asyncio.sleep(3)

            # Confirmar dialogs de aviso
            for btn_text in ["Run anyway", "Executar assim mesmo", "Sim", "Yes", "OK"]:
                try:
                    await page.click(f'button:has-text("{btn_text}")', timeout=2000)
                    _log(f"Dialog confirmado: {btn_text}")
                    break
                except Exception:
                    pass

            # ── 6. Aguardar download (ate 90 min) ─────────────────
            _update_step("Treinando no Colab — aguardando conclusao...")
            _log("Treinamento iniciado. Chrome ficara aberto.")
            _log("O modelo sera baixado automaticamente ao terminar.")

            start = asyncio.get_event_loop().time()
            while not download_event.is_set():
                elapsed = int(asyncio.get_event_loop().time() - start)
                training_state["metrics"]["step"] = elapsed
                if elapsed % 300 == 0 and elapsed > 0:
                    _log(f"Treinando... {elapsed // 60} min decorridos")
                if elapsed > 5400:  # 90 min
                    raise Exception("Timeout de 90 minutos aguardando download do modelo")
                await asyncio.sleep(10)

            model_path = downloaded_path[0]
            training_state["model_path"] = model_path
            _update_step("Modelo recebido com sucesso!")
            _log(f"Modelo salvo em: {model_path}")
            _log("Va para o Dashboard!")

            await asyncio.sleep(2)

    except Exception as e:
        training_state["error"] = str(e)
        _log(f"Erro: {e}")

    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            proc.wait()
            _log("Chrome fechado")

    training_state["running"] = False
    training_state["finished"] = True
    _log("Automacao Colab finalizada")
