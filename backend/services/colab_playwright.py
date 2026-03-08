import asyncio
import subprocess
from pathlib import Path

import httpx

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
    "Injetando dataset de treinamento...",
    "Instalando dependencias...",
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


def reset_training_state():
    """Reseta o estado de treinamento. Chamado ANTES da background task iniciar."""
    training_state.update({
        "running": True, "step": "", "steps_done": [], "log": [],
        "metrics": {"epoch": 0, "loss": None, "step": 0},
        "finished": False, "error": "", "model_path": "",
    })


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


def _has_saved_login(profile_dir: Path) -> bool:
    """Verifica se o perfil persistente ja tem cookies salvos (login anterior).

    Retorna False se o marker .login-expired existir (login expirou em headless).
    """
    # Se login expirou na ultima execucao, forcar headed
    expired_marker = profile_dir / ".login-expired"
    if expired_marker.exists():
        expired_marker.unlink()  # limpar marker — proxima vez tenta headless de novo
        return False
    # Chrome salva cookies em Default/Cookies ou Default/Network/Cookies
    for cookie_path in [
        profile_dir / "Default" / "Cookies",
        profile_dir / "Default" / "Network" / "Cookies",
    ]:
        if cookie_path.exists() and cookie_path.stat().st_size > 0:
            return True
    return False


def _launch_chrome(profile_dir: Path, headless: bool = False) -> subprocess.Popen:
    """Lanca Chrome com perfil persistente.

    Se headless=True, usa --headless=new (Chrome 112+) que e identico ao headed
    em user-agent e comportamento JS, permitindo reusar cookies de login.
    """
    chrome = _find_chrome()
    mode = "headless" if headless else "headed"
    _log(f"Chrome: {chrome} ({mode})")
    args = [
        chrome,
        f"--remote-debugging-port={_CDP_PORT}",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if headless:
        args.append("--headless=new")
        args.append("--window-size=1920,1080")
    else:
        args.append("--start-maximized")
    args.append("https://colab.research.google.com")

    proc = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _log(f"Chrome iniciado (PID {proc.pid})")
    return proc


async def _wait_cdp(timeout_s: int = 20):
    async with httpx.AsyncClient() as client:
        for _ in range(timeout_s * 2):
            try:
                await client.get(f"{_CDP_URL}/json", timeout=1)
                return
            except Exception:
                await asyncio.sleep(0.5)
    raise RuntimeError("CDP nao respondeu — Chrome nao iniciou corretamente")


def _poll_gguf_files(directory: Path) -> Path | None:
    """Procura arquivos .gguf no diretorio de download."""
    for f in directory.iterdir():
        if f.suffix == ".gguf" and f.stat().st_size > 0:
            return f
    return None


async def _inject_dataset(page, dataset_path: Path, timeout_s: int = 300):
    """Detecta o widget files.upload() do Colab e injeta o dataset automaticamente.

    Quando a Cell de upload executa `files.upload()`, o Colab renderiza um
    <input type="file"> dentro de um output-area. Esse input e diferente
    do input de upload de notebook — aparece dentro de .output-area ou
    .outputarea (pode variar). Polling ate ele aparecer.
    """
    _log(f"Aguardando widget de upload do dataset... (ate {timeout_s}s)")

    for i in range(timeout_s):
        # Procurar inputs de arquivo dentro das areas de output das celulas
        file_inputs = await page.query_selector_all(
            '.output-area input[type="file"], '
            '.outputarea input[type="file"], '
            'div[class*="output"] input[type="file"]'
        )
        if file_inputs:
            # Pegar o ultimo input (o mais recente, da celula de upload)
            target_input = file_inputs[-1]
            await target_input.set_input_files(str(dataset_path))
            _log(f"Dataset injetado: {dataset_path.name}")
            return True

        # Fallback: qualquer input[type="file"] que NAO seja o do menu Arquivo
        all_inputs = await page.query_selector_all('input[type="file"]')
        for inp in all_inputs:
            # Checar se e visivel e esta dentro de um output
            visible = await inp.is_visible()
            if visible:
                await inp.set_input_files(str(dataset_path))
                _log(f"Dataset injetado (fallback): {dataset_path.name}")
                return True

        await asyncio.sleep(1)

    _log("AVISO: Widget de upload do dataset nao apareceu — upload manual necessario")
    return False


async def run_colab_automation(notebook_path: Path, dataset_path: Path, model_out_dir: Path):
    """
    Automacao completa do Google Colab usando Chrome real via subprocess + CDP.

    Primeira execucao: Chrome headed (com tela) para login manual do Google.
    Execucoes seguintes: Chrome headless (sem tela), cookies reutilizados.

    Perfil persistente em .colab-profile/ salva o login entre sessoes.

    Fluxo:
      1. Lanca Chrome (headed ou headless) → navega para Colab
      2. Detecta login (ausencia do botao 'Fazer login') — aguarda ate 5 min
      3. ESC para fechar dialog inicial
      4. Arquivo > Fazer upload de notebook → injeta notebook_path
      5. Ambiente de execucao > Alterar tipo → seleciona GPUs: T4 → Salvar
      6. Ctrl+F9 → Run all → confirma dialogs
      7. Detecta files.upload() widget → injeta dataset automaticamente
      8. Detecta download .gguf via polling + page.on("download") → salva em model_out_dir
      9. Fecha Chrome
    """
    # Estado ja foi resetado pelo router (reset_training_state) antes da task iniciar.
    training_state["step"] = STEPS[0]

    PROJECT_ROOT = Path(__file__).parent.parent.parent
    PROFILE_DIR  = PROJECT_ROOT / ".colab-profile"
    model_out_dir.mkdir(parents=True, exist_ok=True)

    # Decidir modo: headless se ja tem login salvo, headed na primeira vez
    use_headless = _has_saved_login(PROFILE_DIR)

    download_event = asyncio.Event()
    downloaded_path: list[str] = []
    proc = None

    try:
        from playwright.async_api import async_playwright

        # ── 1. Lançar Chrome ──────────────────────────────────────
        _update_step(STEPS[0])
        if use_headless:
            _log("Login salvo detectado — usando modo headless (sem tela)")
        else:
            _log("Primeiro uso — abrindo Chrome com tela para login manual")
        _log("Perfil persistente em .colab-profile/")
        proc = _launch_chrome(PROFILE_DIR, headless=use_headless)
        await _wait_cdp()
        _log("CDP pronto — conectando Playwright...")

        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(_CDP_URL)
            ctx  = browser.contexts[0]
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()

            # Configurar download via Page.setDownloadBehavior (substitui Browser.setDownloadBehavior deprecado)
            cdp_session = await ctx.new_cdp_session(page)
            try:
                await cdp_session.send("Page.setDownloadBehavior", {
                    "behavior": "allow",
                    "downloadPath": str(model_out_dir),
                })
            except Exception:
                # Fallback para Chrome mais antigo
                await cdp_session.send("Browser.setDownloadBehavior", {
                    "behavior": "allow",
                    "downloadPath": str(model_out_dir),
                })

            # Handler de download — registrado antes de Run all.
            # Pode nao disparar via CDP, por isso ha fallback de polling abaixo.
            async def on_download(download):
                fname     = download.suggested_filename
                save_path = model_out_dir / fname
                _log(f"Download event recebido: {fname}")
                # Polling ate o arquivo estar completo (tamanho estabilizar)
                prev_size = -1
                for _ in range(600):  # ate 5 min de polling
                    if save_path.exists():
                        cur_size = save_path.stat().st_size
                        if cur_size > 0 and cur_size == prev_size:
                            break
                        prev_size = cur_size
                    await asyncio.sleep(0.5)
                _log(f"Download concluido: {fname} ({save_path.stat().st_size / (1024**3):.2f} GB)")
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
            # Minimo 2 checks consecutivos sem botao de login para confirmar
            consecutive_ok = 0
            for i in range(100):  # ate 5 min (100 × 3s)
                try:
                    url = page.url
                    if "accounts.google.com" in url:
                        consecutive_ok = 0
                        if use_headless:
                            # Headless mas redirecionou pro login — cookies expiraram
                            _log("Cookies expiraram — reinicie sem headless para login manual")
                            raise Exception(
                                "Login expirado. Execute novamente — Chrome abrira com tela para login."
                            )
                        if i == 0:
                            _log("Pagina de login do Google aberta — faca login no Chrome")
                        training_state["metrics"]["step"] = i * 3
                        await asyncio.sleep(3)
                        continue
                    sign_in = await page.query_selector(
                        'a[aria-label="Fazer login"],a[aria-label="Sign in"]'
                    )
                    if sign_in:
                        consecutive_ok = 0
                        if use_headless:
                            _log("Botao de login visivel em headless — cookies expiraram")
                            raise Exception(
                                "Login expirado. Execute novamente — Chrome abrira com tela para login."
                            )
                        if i == 0:
                            _log("Botao 'Fazer login' visivel — faca login no Chrome")
                        elif i % 10 == 0:
                            _log(f"Aguardando login... {i * 3}s")
                        training_state["metrics"]["step"] = i * 3
                        await asyncio.sleep(3)
                        continue
                    # Sem botao de login — confirmar com check consecutivo
                    consecutive_ok += 1
                    if consecutive_ok >= 2:
                        logged_in = True
                        break
                    await asyncio.sleep(2)
                except Exception as e:
                    if "Login expirado" in str(e):
                        # Invalidar cookies para forcar headed na proxima vez
                        raise
                    consecutive_ok = 0
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

            # ── 6. Injetar dataset automaticamente ────────────────
            _update_step(STEPS[5])
            _log("Aguardando celula de upload do dataset...")
            # Cells 0-3 (title, config, install, imports) executam antes da Cell 4 (upload).
            # pip install pode levar 30-60s. Aguardar ate 5 min para o widget aparecer.
            dataset_injected = await _inject_dataset(page, dataset_path, timeout_s=300)
            if dataset_injected:
                _log("Dataset injetado com sucesso — treinamento continuara automaticamente")
            else:
                _log("Upload manual necessario — faca upload no Chrome")

            # ── 7. Aguardar download (ate 90 min) ─────────────────
            _update_step("Treinando no Colab — aguardando conclusao...")
            _log("Treinamento iniciado. Aguardando download do modelo GGUF.")

            start = asyncio.get_event_loop().time()
            while not download_event.is_set():
                elapsed = int(asyncio.get_event_loop().time() - start)
                training_state["metrics"]["step"] = elapsed
                if elapsed % 300 == 0 and elapsed > 0:
                    _log(f"Treinando... {elapsed // 60} min decorridos")
                if elapsed > 5400:  # 90 min
                    raise Exception("Timeout de 90 minutos aguardando download do modelo")

                # Fallback: polling direto do diretorio de download
                # para o caso de page.on("download") nao disparar via CDP
                gguf_file = _poll_gguf_files(model_out_dir)
                if gguf_file:
                    # Verificar se o download terminou (tamanho estavel por 10s)
                    size1 = gguf_file.stat().st_size
                    await asyncio.sleep(10)
                    size2 = gguf_file.stat().st_size
                    if size2 > 0 and size1 == size2:
                        _log(f"Download detectado via polling: {gguf_file.name} ({size2 / (1024**3):.2f} GB)")
                        downloaded_path.append(str(gguf_file))
                        download_event.set()
                        break

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
        # Se login expirou em headless, invalidar flag para forcar headed na proxima
        if "Login expirado" in str(e):
            expired_marker = PROJECT_ROOT / ".colab-profile" / ".login-expired"
            expired_marker.write_text("expired")

    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
            _log("Chrome fechado")

    training_state["running"] = False
    training_state["finished"] = True
    _log("Automacao Colab finalizada")
