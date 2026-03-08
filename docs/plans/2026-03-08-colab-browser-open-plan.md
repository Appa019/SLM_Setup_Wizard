# Colab Browser Open Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Substituir a automação Playwright (que falha no login do Google) por `webbrowser.open()` + monitoramento de pasta para a integração com o Google Colab.

**Architecture:** `run_colab_automation()` em `colab_playwright.py` abre o Colab no browser real do usuário via `webbrowser.open()`, exibe instruções no log via `_log()`, e monitora `models/` a cada 10s aguardando um `.gguf`. O `training_state` e o SSE ficam inalterados — o frontend já funciona corretamente com esse contrato.

**Tech Stack:** Python stdlib (`webbrowser`, `asyncio`, `pathlib`), FastAPI, React (sem mudanças)

---

## Task 1: Reescrever `run_colab_automation()` em `colab_playwright.py`

**Files:**
- Modify: `backend/services/colab_playwright.py`

**Step 1: Ler o arquivo atual**

```bash
cat backend/services/colab_playwright.py
```

Confirmar que `run_colab_automation` existe na linha ~39 e que `_log`, `_update_step`, `training_state` estão definidos acima.

**Step 2: Substituir o corpo de `run_colab_automation()`**

Manter a assinatura e o `training_state` init block. Substituir **apenas** o bloco `try:` em diante pelo código abaixo:

```python
async def run_colab_automation(notebook_path: Path, dataset_path: Path, model_out_dir: Path):
    """
    Abre o Google Colab no browser padrao do sistema e monitora a pasta models/
    aguardando o arquivo .gguf gerado pelo treinamento.
    """
    import webbrowser

    global training_state
    training_state.update({
        "running": True, "step": STEPS[0], "steps_done": [], "log": [],
        "metrics": {"epoch": 0, "loss": None, "step": 0},
        "finished": False, "error": "", "model_path": "",
    })

    try:
        # Passo 1: Abrir Colab no browser real do usuario
        _update_step(STEPS[0])
        colab_url = "https://colab.research.google.com"
        _log(f"Abrindo {colab_url} no browser padrao...")
        webbrowser.open(colab_url)
        await asyncio.sleep(3)

        # Passo 2: Instruções para o usuario
        _update_step("Aguardando acoes manuais no Colab...")
        _log("=" * 42)
        _log("ACOES NECESSARIAS NO BROWSER:")
        _log("1. Faca login na conta Google se solicitado")
        _log("2. File > Upload notebook")
        _log(f"   Arquivo: {notebook_path.name}")
        _log("3. Runtime > Change runtime type > T4 GPU")
        _log("4. Runtime > Run all  (Ctrl+F9)")
        _log("5. Na celula de upload: selecione training_data.jsonl")
        _log(f"6. Aguarde o fim e faca download do modelo_final.gguf")
        _log(f"   Salve em: {model_out_dir}/")
        _log("=" * 42)

        # Passo 3: Monitorar models/ aguardando .gguf
        _update_step("Monitorando pasta models/ aguardando modelo_final.gguf...")
        model_out_dir.mkdir(parents=True, exist_ok=True)

        for i in range(360):  # ate 60 minutos (360 x 10s)
            await asyncio.sleep(10)
            elapsed = (i + 1) * 10
            _log(f"Aguardando .gguf... {elapsed}s decorridos")
            training_state["metrics"]["step"] = elapsed

            gguf_files = list(model_out_dir.glob("*.gguf"))
            if gguf_files:
                model_path = str(gguf_files[0])
                _log(f"Modelo GGUF detectado: {gguf_files[0].name}")
                training_state["model_path"] = model_path
                _update_step("Modelo recebido com sucesso!")
                break
        else:
            _log("Timeout de 60 minutos atingido sem detectar .gguf.")
            _log("Se o modelo ja foi baixado, coloque o .gguf em models/ e reinicie o dashboard.")

    except Exception as e:
        training_state["error"] = str(e)
        _log(f"Erro: {e}")

    training_state["running"] = False
    training_state["finished"] = True
    _log("Automacao Colab finalizada")
```

**Step 3: Verificar sintaxe**

```bash
cd backend && source ../.venv/bin/activate && python3 -c "from services.colab_playwright import run_colab_automation, get_training_state; print('OK')"
```
Expected: `OK`

**Step 4: Verificar que o backend sobe sem erros**

```bash
timeout 6 uvicorn main:app --host 127.0.0.1 --port 8005 2>&1; echo "exit: $?"
```
Expected: exit code 124 (morto pelo timeout, não por erro de import)

**Step 5: Commit**

```bash
git add backend/services/colab_playwright.py
git commit -m "feat: abrir Colab no browser real do sistema + monitorar models/ para gguf"
```

---

## Task 2: Verificação final + push

**Step 1: Smoke tests**

```bash
cd backend && source ../.venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8006 &
sleep 3
python3 - <<'EOF'
import httpx, sys
BASE = "http://127.0.0.1:8006"
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
kill %1
```
Expected: ambos OK

**Step 2: Push ao GitHub**

```bash
git push origin main
```
