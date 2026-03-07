# Multi-Specialist Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Permitir treinar N especialistas com tópicos distintos e selecionar qual usar no Dashboard, sem que rodadas novas sobrescrevam rodadas anteriores.

**Architecture:** Cada treinamento gera um slug único `{topic}_{model_id}_{timestamp}` usado como nome do GGUF e de um sidecar JSON com metadata. O Dashboard lê os sidecars para exibir informações ricas e expõe botão "Treinar Novo Especialista" que reseta o wizard.

**Tech Stack:** FastAPI, Python pathlib, React, TypeScript, WizardContext, Framer Motion

---

## Task 1: Slug + Sidecar — Backend `colab_manager.py` e `routers/colab.py`

**Files:**
- Modify: `backend/services/colab_manager.py` — adicionar `make_slug()`, passar `model_slug` para output
- Modify: `backend/routers/colab.py` — derivar slug, gravar sidecar, passar slug aos geradores

**Step 1: Adicionar `make_slug()` e atualizar `generate_notebook()` em `colab_manager.py`**

Substituir a abertura do arquivo:

```python
import json
import re
from datetime import datetime
from pathlib import Path

COLAB_DIR      = Path(__file__).parent.parent.parent / "colab"
MODELS_DIR     = Path(__file__).parent.parent.parent / "models"
DATA_PROCESSED = Path(__file__).parent.parent.parent / "data" / "processed"

MODEL_MAP = {
    "llama-3.2-1b": "meta-llama/Llama-3.2-1B-Instruct",
    "llama-3.2-3b": "meta-llama/Llama-3.2-3B-Instruct",
    "phi-3-mini":   "microsoft/Phi-3-mini-4k-instruct",
    "mistral-7b":   "mistralai/Mistral-7B-Instruct-v0.3",
    "qwen2-7b":     "Qwen/Qwen2-7B-Instruct",
}


def make_slug(topic_area: str, model_id: str) -> str:
    """Deriva slug unico: {topic}_{model_id}_{YYYYMMDD-HHMM}."""
    topic_slug = re.sub(r"[^a-z0-9]+", "-", topic_area.lower()).strip("-")[:30]
    ts         = datetime.now().strftime("%Y%m%d-%H%M")
    return f"{topic_slug}_{model_id}_{ts}"


def write_sidecar(slug: str, topic_profile: dict, model_id: str,
                  quant_type: str, training_target: str) -> None:
    """Grava models/{slug}.json com metadata do especialista."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    meta = {
        "slug":            slug,
        "topic":           topic_profile.get("area", "Conhecimento Geral"),
        "subtopics":       topic_profile.get("subtopics", []),
        "base_model":      model_id,
        "quant_type":      quant_type,
        "training_target": training_target,
        "created_at":      datetime.now().isoformat(timespec="seconds"),
    }
    (MODELS_DIR / f"{slug}.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
```

Atualizar assinatura de `generate_notebook` para aceitar `model_slug`:

```python
def generate_notebook(model_id: str, topic_profile: dict,
                      params: dict | None = None,
                      model_slug: str = "especialista") -> Path:
    COLAB_DIR.mkdir(parents=True, exist_ok=True)
    hf_model   = MODEL_MAP.get(model_id, "meta-llama/Llama-3.2-3B-Instruct")
    topic_area = topic_profile.get("area", "conhecimento geral")
    p          = params or {}
    gguf_name  = f"{model_slug}.gguf"
    # ... resto do corpo igual, substituindo "modelo_final.gguf" por gguf_name ...
```

Na célula de conversão GGUF (Cell 11), substituir o nome fixo:
```python
# antes:
"--outfile ./modelo_final.gguf --outtype {GGUF_QUANT_TYPE}\n"
# depois:
f"--outfile ./{gguf_name} --outtype {{GGUF_QUANT_TYPE}}\n"
```

Na célula de download (Cell 12), substituir:
```python
# antes:
"files.download('./modelo_final.gguf')\n"
# depois:
f"files.download('./{gguf_name}')\n"
```

Salvar em path único:
```python
    output_path = COLAB_DIR / f"{model_slug}.ipynb"
    output_path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2))
    return output_path
```

Atualizar `generate_local_script` da mesma forma — adicionar `model_slug: str = "especialista"`,
substituir `local_training.py` por `{model_slug}_local.py` e a instrução de conversão GGUF pelo slug.

**Step 2: Atualizar `routers/colab.py` — derivar slug, gravar sidecar, passar para geradores**

No endpoint `/start`, após o enforcement de `training_target`, adicionar:

```python
from services.colab_manager import generate_notebook, generate_local_script, make_slug, write_sidecar

# Derivar slug unico para este especialista
topic_area  = body.topic_profile.get("area", "especialista")
model_slug  = make_slug(topic_area, body.model_id)

# Gravar sidecar imediatamente (antes de background task)
write_sidecar(
    slug=model_slug,
    topic_profile=body.topic_profile,
    model_id=body.model_id,
    quant_type=body.quant_type,
    training_target=training_target,
)

if training_target == "local":
    script_path = generate_local_script(body.model_id, body.topic_profile, params, model_slug)
    return {"ok": True, "target": "local", "script_path": str(script_path),
            "model_slug": model_slug, "params": params}

notebook_path = generate_notebook(body.model_id, body.topic_profile, params, model_slug)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
background_tasks.add_task(run_colab_automation, notebook_path, dataset_path, MODELS_DIR)
return {"ok": True, "target": "colab", "notebook_path": str(notebook_path),
        "model_slug": model_slug, "params": params}
```

**Step 3: Verificar backend sobe sem erro**

```bash
cd backend && source ../.venv/bin/activate && timeout 6 uvicorn main:app --host 127.0.0.1 --port 8010 2>&1 | grep -E "startup|ERROR|Traceback"
```
Esperado: exit 143 (timeout), sem erros.

**Step 4: Commit**

```bash
git add backend/services/colab_manager.py backend/routers/colab.py
git commit -m "feat: multi-specialist - slug unico por treino, sidecar JSON, nome GGUF dinamico"
```

---

## Task 2: `llama_cpp_runner.py` — Enriquecer lista de modelos com metadata do sidecar

**Files:**
- Modify: `backend/services/llama_cpp_runner.py:13-21` — `find_gguf_models()`

**Step 1: Atualizar `find_gguf_models()` para ler sidecar**

```python
def find_gguf_models() -> list[dict]:
    """Lista todos os .gguf em models/, enriquecendo com sidecar .json se existir."""
    if not MODELS_DIR.exists():
        return []
    models = []
    for f in MODELS_DIR.glob("*.gguf"):
        size_gb  = round(f.stat().st_size / (1024 ** 3), 2)
        sidecar  = f.with_suffix(".json")
        meta: dict = {}
        if sidecar.exists():
            try:
                meta = json.loads(sidecar.read_text(encoding="utf-8"))
            except Exception:
                pass
        models.append({
            "name":            f.name,
            "path":            str(f),
            "size_gb":         size_gb,
            "topic":           meta.get("topic", f.stem),
            "base_model":      meta.get("base_model", ""),
            "quant_type":      meta.get("quant_type", ""),
            "training_target": meta.get("training_target", ""),
            "created_at":      meta.get("created_at", ""),
            "subtopics":       meta.get("subtopics", []),
        })
    return sorted(models, key=lambda m: m.get("created_at", m["name"]), reverse=True)
```

Adicionar import no topo:
```python
import json
```

**Step 2: Verificar backend**

```bash
cd backend && source ../.venv/bin/activate && timeout 6 uvicorn main:app --host 127.0.0.1 --port 8011 2>&1 | grep -E "startup|ERROR|Traceback"
```
Esperado: exit 143 sem erros.

**Step 3: Commit**

```bash
git add backend/services/llama_cpp_runner.py
git commit -m "feat: llama_cpp_runner enriquece modelos com metadata do sidecar JSON"
```

---

## Task 3: `WizardContext.tsx` — Adicionar `resetWizard()`

**Files:**
- Modify: `frontend/src/context/WizardContext.tsx`

**Step 1: Adicionar `resetWizard` ao contexto**

Atualizar `WizardContextValue`:
```tsx
interface WizardContextValue {
  state: WizardState
  update: (patch: Partial<WizardState>) => void
  resetWizard: () => void
  currentStep: number
  setCurrentStep: (step: number) => void
}
```

Dentro de `WizardProvider`, adicionar:
```tsx
const resetWizard = () => {
  setState(defaultState)
  setCurrentStep(1)
}
```

Expor no Provider:
```tsx
<WizardContext.Provider value={{ state, update, resetWizard, currentStep, setCurrentStep }}>
```

**Step 2: Build para verificar tipos**

```bash
cd frontend && npm run build 2>&1 | tail -5
```
Esperado: `✓ built in X.XXs`

**Step 3: Commit**

```bash
git add frontend/src/context/WizardContext.tsx
git commit -m "feat: WizardContext - adicionar resetWizard() para iniciar novo especialista"
```

---

## Task 4: `10_Dashboard.tsx` — Cards de especialista + botão "Treinar Novo"

**Files:**
- Modify: `frontend/src/pages/10_Dashboard.tsx`

**Step 1: Atualizar interface `ModelStatus` para incluir metadata**

```tsx
interface ModelInfo {
  name:            string
  path:            string
  size_gb:         number
  topic:           string
  base_model:      string
  quant_type:      string
  training_target: string
  created_at:      string
  subtopics:       string[]
}

interface ModelStatus {
  llama_available: boolean
  models:          ModelInfo[]
  server_running:  boolean
  loaded_model:    string
  server_port:     number | null
}
```

**Step 2: Substituir lista de modelos por cards enriquecidos**

Substituir o bloco `{status && status.models.length > 0 && (...)}` pelo seguinte:

```tsx
{status && status.models.length > 0 && (
  <div className="space-y-1.5">
    <p className="section-title">Especialistas treinados</p>
    {status.models.map(m => {
      const isLoaded   = status.loaded_model === m.name && running
      const isSelected = selected === m.name
      const dateStr    = m.created_at
        ? new Date(m.created_at).toLocaleDateString('pt-BR')
        : ''
      const targetBadge = m.training_target === 'local' ? 'badge-blue' : 'badge-gray'
      return (
        <label
          key={m.name}
          className={`flex items-start gap-2.5 p-3 rounded border cursor-pointer transition-colors
            ${isSelected
              ? 'border-accent-500 bg-accent-50'
              : 'border-surface-200 hover:border-surface-300'}`}
        >
          <input
            type="radio" name="model" value={m.name}
            checked={isSelected}
            onChange={() => setSelected(m.name)}
            className="accent-accent-500 mt-1 flex-shrink-0"
          />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="text-sm font-semibold text-gray-900 truncate">
                {m.topic || m.name}
              </p>
              {isLoaded && <CheckCircle2 size={13} className="text-success-600 flex-shrink-0" />}
            </div>
            <div className="flex items-center gap-2 mt-0.5 flex-wrap">
              {m.base_model && <span className="code">{m.base_model}</span>}
              {m.quant_type && <span className="code">{m.quant_type.toUpperCase()}</span>}
              <span className="text-[11px] text-gray-400">{m.size_gb} GB</span>
              {m.training_target && (
                <span className={`${targetBadge} text-[10px]`}>
                  {m.training_target === 'local' ? 'GPU local' : 'Colab T4'}
                </span>
              )}
              {dateStr && <span className="text-[11px] text-gray-400">{dateStr}</span>}
            </div>
            {m.subtopics && m.subtopics.length > 0 && (
              <p className="text-[10px] text-gray-400 mt-0.5 truncate">
                {m.subtopics.slice(0, 4).join(' · ')}
              </p>
            )}
          </div>
        </label>
      )
    })}
  </div>
)}
```

**Step 3: Adicionar botão "Treinar Novo Especialista"**

No topo do componente, importar `useWizard` e `useNavigate`:
```tsx
import { useWizard } from '../context/WizardContext'
// (useNavigate já está importado)

const { setCurrentStep, resetWizard } = useWizard()  // adicionar resetWizard
```

No bloco de action buttons (após `{running && <button ...Parar...>}`), adicionar:
```tsx
<button
  onClick={() => { resetWizard(); navigate('/settings') }}
  className="btn-secondary ml-auto"
>
  <Plus size={13} />
  Treinar Novo Especialista
</button>
```

Importar `Plus` do lucide-react:
```tsx
import { Cpu, FolderOpen, Play, Square, Send, RefreshCw, CheckCircle2, AlertCircle, Terminal, Plus } from 'lucide-react'
```

**Step 4: Verificar CSS — garantir `badge-blue` existe em `global.css`**

Se não existir, adicionar em `frontend/src/styles/global.css`:
```css
.badge-blue  { @apply inline-flex items-center px-1.5 py-0.5 rounded-sm text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200; }
```

**Step 5: Build**

```bash
cd frontend && npm run build 2>&1 | tail -5
```
Esperado: `✓ built in X.XXs`

**Step 6: Commit final + push**

```bash
git add frontend/src/pages/10_Dashboard.tsx frontend/src/styles/global.css
git commit -m "feat: dashboard multi-specialist - cards ricos, metadata, botao treinar novo"
git push origin main
```

---

## Ordem de Execução

1. Task 1 — slug + sidecar no backend
2. Task 2 — llama_cpp_runner lê sidecar
3. Task 3 — resetWizard no WizardContext
4. Task 4 — Dashboard com cards de especialista + botão novo
