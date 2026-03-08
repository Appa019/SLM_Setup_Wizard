"""
Helper compartilhado para testes Colab via Chrome + CDP.

Abordagem: lanca Chrome via subprocess (sem flags de automacao detectaveis pelo Google)
e conecta o Playwright via CDP. Isso resolve o bloqueio de login do Google.
"""
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT     = Path(__file__).parent.parent.parent
PROFILE  = ROOT / ".colab-profile"
CDP_PORT = 9222
CDP_URL  = f"http://localhost:{CDP_PORT}"

# Caminhos comuns do Chrome no Linux
CHROME_BINS = [
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
    "/opt/google/chrome/chrome",
    "/snap/bin/chromium",
]


def find_chrome() -> str:
    for path in CHROME_BINS:
        if Path(path).exists():
            return path
    raise RuntimeError(
        "Chrome nao encontrado. Instale com:\n"
        "  sudo apt install google-chrome-stable"
    )


def launch_chrome(url: str = "https://colab.research.google.com") -> subprocess.Popen:
    """
    Lanca Chrome normalmente (sem flags de automacao) com debugging port.
    O Google nao detecta este Chrome como automatizado durante o login.
    """
    chrome = find_chrome()
    print(f"Chrome encontrado: {chrome}")
    print(f"Perfil: {PROFILE}")
    proc = subprocess.Popen(
        [
            chrome,
            f"--remote-debugging-port={CDP_PORT}",
            f"--user-data-dir={PROFILE}",
            "--no-first-run",
            "--no-default-browser-check",
            "--start-maximized",
            url,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"Chrome iniciado (PID {proc.pid})")
    return proc


def wait_cdp_ready(timeout_s: int = 20):
    """Aguarda o endpoint CDP ficar disponivel."""
    print("Aguardando CDP estar pronto...")
    for _ in range(timeout_s * 2):
        try:
            urllib.request.urlopen(f"{CDP_URL}/json", timeout=1)
            print("CDP pronto!")
            return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("CDP nao respondeu — Chrome nao iniciou corretamente")
