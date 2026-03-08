# Colab Full Automation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Automatizar completamente o Google Colab usando Chrome real (`channel="chrome"`) com perfil persistente — abre, detecta login, faz upload do notebook, configura T4 GPU, executa todas as células e baixa o `.gguf` automaticamente.

**Architecture:** Playwright com `channel="chrome"` (Chrome instalado no sistema, não Chromium bundled) + `launch_persistent_context` em `.colab-profile/` para salvar a sessão Google entre execuções. Cada etapa é testada isoladamente em `colab/tests/t1_*.py … t5_*.py` antes da integração final em `backend/services/colab_playwright.py`.

**Tech Stack:** Python 3, Playwright async, asyncio, FastAPI background tasks

---

## Task 1: Infraestrutura de testes + verificar Chrome abre

**Files:**
- Create: `colab/tests/t1_chrome_opens.py`

**Step 1: Criar pasta de testes**

```bash
mkdir -p /home/pedropestana/codigos_python/llm_local_personalizado/colab/tests
```

**Step 2: Verificar que Playwright está instalado**

```bash
cd /home/pedropestana/codigos_python/llm_local_personalizado
source .venv/bin/activate
python3 -c "from playwright.async_api import async_playwright; print('Playwright OK')"
```
Expected: `Playwright OK`

Se falhar: `pip install playwright && playwright install chromium`

**Step 3: Criar script de teste**

Criar `colab/tests/t1_chrome_opens.py`:

```python
"""
T1: Verifica que o Chrome real do sistema abre via Playwright channel='chrome'.
Esperado: Chrome abre visualmente, navega para example.com, imprime titulo, fecha.
"""
import asyncio
from pathlib import Path

ROOT    = Path(__file__).parent.parent.parent
PROFILE = ROOT / ".colab-profile"


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        print(f"Abrindo Chrome real (channel='chrome')...")
        print(f"Perfil persistente: {PROFILE}")
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE),
            channel="chrome",
            headless=False,
            args=["--start-maximized"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto("https://example.com")
        title = await page.title()
        print(f"Titulo da pagina: {title}")
        assert "Example" in title, f"Titulo inesperado: {title}"
        await asyncio.sleep(2)
        await ctx.close()
        print("OK - Chrome abriu, navegou e fechou corretamente")


asyncio.run(main())
```

**Step 4: Executar**

```bash
cd /home/pedropestana/codigos_python/llm_local_personalizado
source .venv/bin/activate
python3 colab/tests/t1_chrome_opens.py
```
Expected: Chrome abre visualmente com example.com, imprime `OK - Chrome abriu, navegou e fechou corretamente`.

Se falhar com `"chrome" channel not found`:
```bash
# Verificar se Chrome está instalado
google-chrome --version
# Se não estiver:
# wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
# sudo apt install google-chrome-stable
```

Se falhar com erro de Playwright driver:
```bash
playwright install chrome
```

**Step 5: Commit**

```bash
git add colab/tests/t1_chrome_opens.py
git commit -m "test: T1 verificar Chrome real abre via Playwright channel=chrome"
```

---

## Task 2: Teste isolado — detecção de login no Colab

**Files:**
- Create: `colab/tests/t2_login_detection.py`

**Step 1: Criar script**

Criar `colab/tests/t2_login_detection.py`:

```python
"""
T2: Abre o Colab no Chrome real e detecta se o usuario esta logado.
Se nao estiver logado, aguarda ate 5 minutos (polling 5s).
Esperado: imprime "Login confirmado!" ou aguarda ate voce logar manualmente.

INSTRUCAO: Ao rodar pela primeira vez, o Chrome vai abrir.
Se pedir login, faca login normal na conta Google.
O script vai detectar automaticamente quando voce logar.
"""
import asyncio
from pathlib import Path

ROOT    = Path(__file__).parent.parent.parent
PROFILE = ROOT / ".colab-profile"


async def wait_for_login(page, timeout_s: int = 300) -> bool:
    """Retorna True quando detectar login, False se timeout."""
    for i in range(timeout_s // 5):
        # Colab mostra elemento de conta quando logado
        logged_elem = await page.query_selector(
            '[aria-label*="Google Account"], '
            '[data-email], '
            '.gb_A, '
            'img[aria-label*="Google Account"]'
        )
        sign_in_btn = await page.query_selector(
            'a[href*="accounts.google.com/signin"], '
            'button:has-text("Sign in"), '
            'a:has-text("Sign in")'
        )
        if logged_elem and not sign_in_btn:
            return True
        if i == 0:
            if sign_in_btn:
                print("Nao logado — faca login no Chrome que abriu...")
            else:
                print(f"Aguardando UI carregar... (tentativa {i+1})")
        elif i % 6 == 0:
            print(f"Ainda aguardando login... {i * 5}s")
        await asyncio.sleep(5)
    return False


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE),
            channel="chrome",
            headless=False,
            args=["--start-maximized"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        print("Navegando para o Colab...")
        await page.goto("https://colab.research.google.com", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=15000)
        await asyncio.sleep(3)

        logged = await wait_for_login(page, timeout_s=300)

        if logged:
            print("Login confirmado!")
        else:
            print("FALHA: login nao detectado em 5 minutos")
            # Inspecionar o DOM para ajustar seletores
            print("\n--- Elementos de conta encontrados: ---")
            elems = await page.query_selector_all('[aria-label]')
            for el in elems[:20]:
                label = await el.get_attribute('aria-label')
                tag   = await el.evaluate('el => el.tagName')
                if label:
                    print(f"  <{tag.lower()} aria-label='{label}'>")

        await asyncio.sleep(2)
        await ctx.close()


asyncio.run(main())
```

**Step 2: Executar**

```bash
cd /home/pedropestana/codigos_python/llm_local_personalizado
source .venv/bin/activate
python3 colab/tests/t2_login_detection.py
```
Expected: Chrome abre. Se o perfil já tem login salvo do T1 → `Login confirmado!` imediatamente. Se não → faça login manual, o script detecta e imprime `Login confirmado!`.

**Step 3: Se os seletores não funcionarem**

Adicionar temporariamente no script antes do `ctx.close()`:
```python
# DEBUG: listar aria-labels da página
elems = await page.query_selector_all('[aria-label]')
for el in elems:
    label = await el.get_attribute('aria-label')
    if label and 'google' in label.lower():
        print(f"aria-label encontrado: {label}")
```
Ajustar `wait_for_login()` com o seletor correto encontrado.

**Step 4: Commit**

```bash
git add colab/tests/t2_login_detection.py
git commit -m "test: T2 deteccao de login no Colab"
```

---

## Task 3: Teste isolado — upload de notebook

**Files:**
- Create: `colab/tests/t3_upload_notebook.py`

**Step 1: Criar notebook mínimo de teste**

```bash
python3 - <<'EOF'
import json
nb = {
    "cells": [{
        "cell_type": "code",
        "source": ["print('Hello from Colab!')"],
        "metadata": {}, "outputs": [], "execution_count": None
    }],
    "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
    "nbformat": 4, "nbformat_minor": 4
}
with open('/tmp/test_notebook.ipynb', 'w') as f:
    json.dump(nb, f)
print("Notebook criado: /tmp/test_notebook.ipynb")
EOF
```

**Step 2: Criar script**

Criar `colab/tests/t3_upload_notebook.py`:

```python
"""
T3: Faz upload de um notebook .ipynb no Colab via File > Upload notebook.
Esperado: notebook abre no editor Colab.
PRE-REQUISITO: T2 passou (Chrome logado no perfil .colab-profile).
"""
import asyncio
from pathlib import Path

ROOT      = Path(__file__).parent.parent.parent
PROFILE   = ROOT / ".colab-profile"
NOTEBOOK  = Path("/tmp/test_notebook.ipynb")


async def upload_notebook(page, notebook_path: Path) -> bool:
    print("Clicando no menu File...")
    # Colab usa web components — tentar varios seletores
    for selector in [
        'colab-toolbar-button:has-text("File")',
        '[id*="file"]',
        'text=File',
    ]:
        try:
            await page.click(selector, timeout=5000)
            print(f"  File clicado via: {selector}")
            break
        except Exception:
            continue
    else:
        print("FALHA: nao encontrou menu File")
        # Listar todos os botoes da toolbar para debug
        buttons = await page.query_selector_all('colab-toolbar-button, [role="menuitem"], button')
        print("Botoes encontrados:")
        for b in buttons[:15]:
            t = await b.inner_text()
            if t.strip():
                print(f"  '{t.strip()}'")
        return False

    await asyncio.sleep(1)

    print("Clicando em Upload notebook...")
    for selector in [
        'text=Upload notebook',
        '[data-command="file_upload_notebook"]',
    ]:
        try:
            await page.click(selector, timeout=3000)
            print(f"  Upload notebook clicado via: {selector}")
            break
        except Exception:
            continue
    else:
        print("FALHA: nao encontrou 'Upload notebook'")
        # Listar itens visiveis do menu
        items = await page.query_selector_all('[role="menuitem"]')
        print("Itens de menu encontrados:")
        for item in items:
            t = await item.inner_text()
            if t.strip():
                print(f"  '{t.strip()}'")
        return False

    await asyncio.sleep(2)

    # Injetar arquivo no input[type="file"]
    file_input = await page.query_selector('input[type="file"]')
    if not file_input:
        # Tentar clicar em "Browse" ou "Choose file"
        for sel in ['text=Browse', 'text=Choose file', 'button:has-text("Browse")']:
            try:
                await page.click(sel, timeout=3000)
                file_input = await page.query_selector('input[type="file"]')
                if file_input:
                    break
            except Exception:
                continue

    if not file_input:
        print("FALHA: input[type='file'] nao encontrado")
        print("Conteudo do dialogo:")
        dialogs = await page.query_selector_all('[role="dialog"], mat-dialog-container')
        for d in dialogs:
            print(await d.inner_text())
        return False

    await file_input.set_input_files(str(notebook_path))
    print(f"Arquivo injetado: {notebook_path.name}")
    await asyncio.sleep(4)

    title = await page.title()
    print(f"Titulo da pagina apos upload: {title}")
    return True


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE),
            channel="chrome",
            headless=False,
            args=["--start-maximized"],
            accept_downloads=True,
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto("https://colab.research.google.com", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=15000)
        await asyncio.sleep(4)

        ok = await upload_notebook(page, NOTEBOOK)
        if ok:
            print("OK - Notebook carregado com sucesso")
        else:
            print("FALHA - Verificar seletores acima")

        print("Aguardando 5s para verificacao visual...")
        await asyncio.sleep(5)
        await ctx.close()


asyncio.run(main())
```

**Step 3: Executar**

```bash
cd /home/pedropestana/codigos_python/llm_local_personalizado
source .venv/bin/activate
python3 colab/tests/t3_upload_notebook.py
```
Expected: Chrome abre no Colab (já logado pelo T2), `test_notebook.ipynb` abre no editor.

**Step 4: Ajustar seletores baseado na saída de debug**

Se `upload_notebook()` retornar False, o script imprime os seletores reais encontrados. Ajuste `t3_upload_notebook.py` com os seletores corretos antes de prosseguir.

**Step 5: Commit**

```bash
git add colab/tests/t3_upload_notebook.py
git commit -m "test: T3 upload de notebook no Colab"
```

---

## Task 4: Teste isolado — configurar T4 GPU

**Files:**
- Create: `colab/tests/t4_set_t4_gpu.py`

**Step 1: Criar script**

Criar `colab/tests/t4_set_t4_gpu.py`:

```python
"""
T4: Configura runtime T4 GPU via Runtime > Change runtime type.
Esperado: dialog fecha, runtime confirmado como T4 GPU.
PRE-REQUISITO: T3 passou (notebook aberto no Colab).

Execute este script com um notebook JA ABERTO no Colab
(deixe o Chrome do T3 aberto, ou abra um novo notebook antes de rodar).
"""
import asyncio
from pathlib import Path
import json

ROOT      = Path(__file__).parent.parent.parent
PROFILE   = ROOT / ".colab-profile"
NOTEBOOK  = Path("/tmp/test_notebook.ipynb")


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

    # Inspecionar o dialog para encontrar os seletores corretos
    print("Inspecionando dialog de runtime...")
    selects = await page.query_selector_all('select')
    for s in selects:
        name  = await s.get_attribute('name') or await s.get_attribute('id') or '?'
        value = await s.input_value()
        opts  = await s.evaluate('el => Array.from(el.options).map(o => o.value)')
        print(f"  select name='{name}' value='{value}' options={opts}")

    # Tentar selecionar GPU
    print("Selecionando GPU como accelerator...")
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
        # Tentar clicar em radio button ou option com texto GPU
        for sel in ['text=GPU', '[value="GPU"]', 'mat-radio-button:has-text("GPU")']:
            try:
                await page.click(sel, timeout=3000)
                print(f"  GPU clicado via: {sel}")
                gpu_set = True
                break
            except Exception:
                continue

    if not gpu_set:
        print("FALHA: nao conseguiu selecionar GPU — verificar seletores acima")
        return False

    await asyncio.sleep(1)

    # Tentar selecionar T4 especificamente (se houver subtipo)
    for selector, value in [
        ('select[name="acceleratorSubType"]', 'T4'),
        ('select[name="gpuType"]', 'T4'),
    ]:
        try:
            await page.select_option(selector, value, timeout=3000)
            print(f"  T4 selecionado via: {selector}")
            break
        except Exception:
            pass  # Subtipo pode nao existir

    # Clicar Save
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
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE),
            channel="chrome",
            headless=False,
            args=["--start-maximized"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto("https://colab.research.google.com", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=15000)
        await asyncio.sleep(3)

        # Upload notebook para ter algo aberto
        print("Abrindo notebook de teste...")
        await page.click('text=File', timeout=8000)
        await page.click('text=Upload notebook', timeout=5000)
        await asyncio.sleep(2)
        fi = await page.query_selector('input[type="file"]')
        if fi:
            await fi.set_input_files(str(NOTEBOOK))
            await asyncio.sleep(4)

        ok = await set_t4_gpu(page)
        print("RESULTADO:", "OK" if ok else "FALHA")
        await asyncio.sleep(3)
        await ctx.close()


asyncio.run(main())
```

**Step 2: Executar**

```bash
cd /home/pedropestana/codigos_python/llm_local_personalizado
source .venv/bin/activate
python3 colab/tests/t4_set_t4_gpu.py
```
Expected: dialog "Change runtime type" abre, GPU selecionado, dialog fecha, `OK - T4 GPU configurado!`.

O script imprime todos os `select` e seus `options` reais — use isso para ajustar seletores se necessário.

**Step 3: Commit**

```bash
git add colab/tests/t4_set_t4_gpu.py
git commit -m "test: T4 configurar T4 GPU no Colab"
```

---

## Task 5: Teste isolado — Run all + interceptar download

**Files:**
- Create: `colab/tests/t5_run_and_download.py`

**Step 1: Criar notebook mínimo com download**

```bash
python3 - <<'EOF'
import json
nb = {
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
}
with open('/tmp/test_download.ipynb', 'w') as f:
    json.dump(nb, f)
print("Notebook criado: /tmp/test_download.ipynb")
EOF
```

**Step 2: Criar script**

Criar `colab/tests/t5_run_and_download.py`:

```python
"""
T5: Executa todas as celulas e intercepta o download automatico.
Usa notebook minimo que cria um arquivo .gguf fake e chama files.download().
Esperado: arquivo 'test_model.gguf' salvo em /tmp/colab_dl/.

IMPORTANTE: Este teste cria uma sessao de runtime no Colab — ele pode demorar
1-2 minutos para conectar ao runtime antes de executar as celulas.
"""
import asyncio
from pathlib import Path

ROOT      = Path(__file__).parent.parent.parent
PROFILE   = ROOT / ".colab-profile"
NOTEBOOK  = Path("/tmp/test_download.ipynb")
SAVE_DIR  = Path("/tmp/colab_dl")
SAVE_DIR.mkdir(exist_ok=True)


async def main():
    from playwright.async_api import async_playwright

    downloaded_file = None
    download_event  = asyncio.Event()

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE),
            channel="chrome",
            headless=False,
            args=["--start-maximized"],
            accept_downloads=True,
            downloads_path=str(SAVE_DIR),
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        # Registrar handler ANTES de qualquer acao
        async def on_download(download):
            nonlocal downloaded_file
            fname     = download.suggested_filename
            save_path = SAVE_DIR / fname
            print(f"  -> Download iniciado: {fname}")
            await download.save_as(str(save_path))
            downloaded_file = str(save_path)
            print(f"  -> Salvo em: {save_path}")
            download_event.set()

        page.on("download", on_download)

        # Navegar e fazer upload do notebook de teste
        print("Navegando para o Colab...")
        await page.goto("https://colab.research.google.com", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=15000)
        await asyncio.sleep(4)

        print("Fazendo upload do notebook de teste...")
        await page.click('text=File', timeout=8000)
        await page.click('text=Upload notebook', timeout=5000)
        await asyncio.sleep(2)
        fi = await page.query_selector('input[type="file"]')
        if fi:
            await fi.set_input_files(str(NOTEBOOK))
        else:
            print("FALHA: input[type='file'] nao encontrado — rode T3 primeiro para ajustar seletores")
            await ctx.close()
            return
        await asyncio.sleep(4)

        # Run all via Ctrl+F9
        print("Executando todas as celulas (Ctrl+F9)...")
        await page.keyboard.press("Control+F9")
        await asyncio.sleep(2)

        # Confirmar dialogs que possam aparecer
        for btn_text in ["Run anyway", "Yes", "OK", "Executar mesmo assim"]:
            try:
                await page.click(f'button:has-text("{btn_text}")', timeout=2000)
                print(f"  Dialog confirmado: '{btn_text}'")
                break
            except Exception:
                pass

        # Aguardar download (max 3 minutos para este teste simples)
        print("Aguardando execucao e download...")
        print("(O Colab precisa conectar ao runtime — pode levar 1-2 min)")
        try:
            await asyncio.wait_for(download_event.wait(), timeout=180)
            print(f"\nSUCESSO: arquivo salvo em {downloaded_file}")

            # Verificar conteudo
            content = Path(downloaded_file).read_text()
            assert "fake gguf" in content, f"Conteudo inesperado: {content}"
            print("Conteudo do arquivo verificado OK")

        except asyncio.TimeoutError:
            print("\nTIMEOUT: download nao ocorreu em 3 minutos")
            print("Possiveis causas:")
            print("  - Runtime nao conectou (verificar status no Chrome)")
            print("  - Celula com erro (verificar output no Chrome)")
            print("  - Dialog de confirmacao nao foi aceito")

        await asyncio.sleep(3)
        await ctx.close()


asyncio.run(main())
```

**Step 3: Executar**

```bash
cd /home/pedropestana/codigos_python/llm_local_personalizado
source .venv/bin/activate
python3 colab/tests/t5_run_and_download.py
```
Expected (após 1-2 min para runtime conectar):
```
Navegando para o Colab...
Fazendo upload do notebook de teste...
Executando todas as celulas (Ctrl+F9)...
Aguardando execucao e download...
  -> Download iniciado: test_model.gguf
  -> Salvo em: /tmp/colab_dl/test_model.gguf
SUCESSO: arquivo salvo em /tmp/colab_dl/test_model.gguf
Conteudo do arquivo verificado OK
```

**Step 4: Commit**

```bash
git add colab/tests/t5_run_and_download.py
git commit -m "test: T5 run all + interceptar download no Colab"
```

---

## Task 6: Implementar `run_colab_automation()` completo

**Files:**
- Modify: `backend/services/colab_playwright.py`

**Step 1: Ler arquivo atual**

```bash
cat backend/services/colab_playwright.py
```

Confirmar que `STEPS`, `training_state`, `get_training_state()`, `_log()`, `_update_step()` estão definidos.

**Step 2: Substituir `run_colab_automation()`**

Substituir o corpo completo da função (manter `STEPS`, `training_state`, helpers):

```python
async def run_colab_automation(notebook_path: Path, dataset_path: Path, model_out_dir: Path):
    """
    Automacao completa do Google Colab usando Chrome real (channel='chrome').
    Perfil persistente em .colab-profile/ salva o login entre sessoes.
    Fluxo: abre Chrome -> detecta login -> upload notebook -> T4 GPU -> Run all
           -> intercepta download .gguf -> salva em models/ -> fecha browser.
    """
    from playwright.async_api import async_playwright

    global training_state
    training_state.update({
        "running": True, "step": STEPS[0], "steps_done": [], "log": [],
        "metrics": {"epoch": 0, "loss": None, "step": 0},
        "finished": False, "error": "", "model_path": "",
    })

    PROFILE_DIR = Path(__file__).parent.parent.parent / ".colab-profile"
    model_out_dir.mkdir(parents=True, exist_ok=True)

    download_event  = asyncio.Event()
    downloaded_path: list[str] = []

    try:
        async with async_playwright() as p:

            # ── 1. Abrir Chrome real com perfil persistente ──────────────
            _update_step(STEPS[0])
            _log("Abrindo Chrome com perfil persistente em .colab-profile/")
            _log("(Login sera salvo automaticamente apos a primeira vez)")
            ctx = await p.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE_DIR),
                channel="chrome",
                headless=False,
                args=["--start-maximized"],
                accept_downloads=True,
                downloads_path=str(model_out_dir),
            )
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()

            # Registrar handler de download antes de qualquer acao
            async def on_download(download):
                fname     = download.suggested_filename
                save_path = model_out_dir / fname
                await download.save_as(str(save_path))
                _log(f"Download concluido: {fname}")
                downloaded_path.append(str(save_path))
                download_event.set()

            page.on("download", on_download)

            # ── 2. Navegar para o Colab ──────────────────────────────────
            _log("Navegando para colab.research.google.com...")
            await page.goto("https://colab.research.google.com", timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=15000)
            await asyncio.sleep(3)

            # ── 3. Detectar login (aguarda ate 5 min) ────────────────────
            _update_step(STEPS[1])
            logged_in = False
            for i in range(60):
                logged_elem = await page.query_selector(
                    '[aria-label*="Google Account"], [data-email], .gb_A, '
                    'img[aria-label*="Google Account"]'
                )
                sign_in_btn = await page.query_selector(
                    'a[href*="accounts.google.com/signin"], '
                    'button:has-text("Sign in"), a:has-text("Sign in")'
                )
                if logged_elem and not sign_in_btn:
                    logged_in = True
                    break
                if i == 0:
                    _log("Aguardando login no Chrome... (faca login se solicitado)")
                training_state["metrics"]["step"] = (i + 1) * 5
                await asyncio.sleep(5)

            if not logged_in:
                raise Exception("Login nao detectado em 5 minutos — faca login no Chrome")

            _log("Login confirmado!")

            # ── 4. Upload do notebook ────────────────────────────────────
            _update_step(STEPS[2])
            _log(f"Fazendo upload: {notebook_path.name}")
            await page.click('text=File', timeout=10000)
            await page.click('text=Upload notebook', timeout=5000)
            await asyncio.sleep(2)

            file_input = await page.query_selector('input[type="file"]')
            if not file_input:
                for sel in ['text=Browse', 'text=Choose file']:
                    try:
                        await page.click(sel, timeout=3000)
                        file_input = await page.query_selector('input[type="file"]')
                        if file_input:
                            break
                    except Exception:
                        pass

            if not file_input:
                raise Exception("Input de upload nao encontrado — UI do Colab pode ter mudado")

            await file_input.set_input_files(str(notebook_path))
            await asyncio.sleep(4)
            _log("Notebook carregado no Colab")

            # ── 5. Configurar T4 GPU ─────────────────────────────────────
            _update_step(STEPS[3])
            _log("Configurando runtime T4 GPU...")
            await page.click('text=Runtime', timeout=10000)
            await page.click('text=Change runtime type', timeout=5000)
            await asyncio.sleep(2)

            gpu_set = False
            for selector, value in [
                ('select[name="acceleratorType"]', 'GPU'),
                ('select[name="hardwareAccelerator"]', 'GPU'),
            ]:
                try:
                    await page.select_option(selector, value, timeout=5000)
                    gpu_set = True
                    break
                except Exception:
                    pass

            if not gpu_set:
                for sel in ['text=GPU', '[value="GPU"]', 'mat-radio-button:has-text("GPU")']:
                    try:
                        await page.click(sel, timeout=3000)
                        gpu_set = True
                        break
                    except Exception:
                        pass

            if not gpu_set:
                _log("Aviso: nao conseguiu selecionar GPU automaticamente")

            for selector, value in [
                ('select[name="acceleratorSubType"]', 'T4'),
                ('select[name="gpuType"]', 'T4'),
            ]:
                try:
                    await page.select_option(selector, value, timeout=3000)
                    break
                except Exception:
                    pass

            await page.click('button:has-text("Save")', timeout=5000)
            await asyncio.sleep(2)
            _log("T4 GPU configurado")

            # ── 6. Run all ────────────────────────────────────────────────
            _update_step(STEPS[4])
            _log("Iniciando execucao de todas as celulas (Ctrl+F9)...")
            await page.keyboard.press("Control+F9")
            await asyncio.sleep(2)

            for btn_text in ["Run anyway", "Yes", "OK", "Executar mesmo assim"]:
                try:
                    await page.click(f'button:has-text("{btn_text}")', timeout=2000)
                    _log(f"Dialog confirmado: {btn_text}")
                    break
                except Exception:
                    pass

            # ── 7. Aguardar download (ate 90 minutos) ────────────────────
            _update_step("Treinando no Colab — aguardando conclusao...")
            _log("Treinamento iniciado. O Chrome ficara aberto.")
            _log("Quando terminar, o modelo sera baixado automaticamente.")

            start = asyncio.get_event_loop().time()
            while not download_event.is_set():
                elapsed = int(asyncio.get_event_loop().time() - start)
                training_state["metrics"]["step"] = elapsed
                if elapsed > 0 and elapsed % 300 == 0:
                    _log(f"Treinando... {elapsed // 60} min decorridos")
                if elapsed > 5400:
                    raise Exception("Timeout de 90 minutos aguardando download")
                await asyncio.sleep(10)

            model_path = downloaded_path[0]
            training_state["model_path"] = model_path
            _update_step("Modelo recebido com sucesso!")
            _log(f"Modelo salvo em: {model_path}")
            _log("Voce ja pode ir para o Dashboard!")

            await asyncio.sleep(2)
            await ctx.close()

    except Exception as e:
        training_state["error"] = str(e)
        _log(f"Erro: {e}")

    training_state["running"] = False
    training_state["finished"] = True
    _log("Automacao Colab finalizada")
```

**Step 3: Verificar sintaxe**

```bash
cd /home/pedropestana/codigos_python/llm_local_personalizado/backend
source ../.venv/bin/activate
python3 -c "from services.colab_playwright import run_colab_automation, get_training_state; print('OK')"
```
Expected: `OK`

**Step 4: Verificar backend sobe**

```bash
timeout 6 uvicorn main:app --host 127.0.0.1 --port 8008 2>&1; echo "exit: $?"
```
Expected: exit 124 (morto pelo timeout, não por erro de import)

**Step 5: Commit**

```bash
git add backend/services/colab_playwright.py
git commit -m "feat: automacao completa Colab - Chrome real, login persistente, T4 GPU, download automatico"
```

---

## Task 7: .gitignore + smoke tests + push

**Step 1: Adicionar `.colab-profile/` ao .gitignore**

```bash
cd /home/pedropestana/codigos_python/llm_local_personalizado
echo ".colab-profile/" >> .gitignore
```

**Step 2: Smoke tests**

```bash
source .venv/bin/activate && cd backend
uvicorn main:app --host 127.0.0.1 --port 8009 &
sleep 3
VENV_PY=/home/pedropestana/codigos_python/llm_local_personalizado/.venv/bin/python3
$VENV_PY - <<'EOF'
import httpx, sys
BASE = "http://127.0.0.1:8009"
ok = True
def check(label, r, expected=200):
    global ok
    s = "OK" if r.status_code == expected else "FAIL"
    if r.status_code != expected: ok = False
    print(f"  {s} {label}: HTTP {r.status_code}")
c = httpx.Client(timeout=10)
check("GET /api/health",       c.get(f"{BASE}/api/health"))
check("GET /api/colab/state",  c.get(f"{BASE}/api/colab/state"))
print("Todos OK" if ok else "FALHAS")
sys.exit(0 if ok else 1)
EOF
kill %1 2>/dev/null
```
Expected: ambos OK

**Step 3: Commit + push**

```bash
cd /home/pedropestana/codigos_python/llm_local_personalizado
git add .gitignore colab/tests/
git commit -m "chore: adicionar .colab-profile ao gitignore"
git push origin main
```
