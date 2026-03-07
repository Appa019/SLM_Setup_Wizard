# Design: Multi-Specialist — Treinar e Usar Múltiplos Especialistas

## Goal
Permitir treinar N especialistas distintos (cada um com tópico/modelo/data diferentes) e selecionar qual usar no Dashboard, sem que rodadas novas sobrescrevam rodadas anteriores.

## Decisão de naming
Opção A aprovada: nome automático derivado do tópico + model_id + timestamp.

```
slug = sanitize(topic_profile["area"])[:30] + "_" + model_id + "_" + YYYYMMDD-HHMM
ex:  "direito-tributario_llama-3.2-3b_20260306-1432"
arquivo GGUF: models/direito-tributario_llama-3.2-3b_20260306-1432.gguf
sidecar JSON: models/direito-tributario_llama-3.2-3b_20260306-1432.json
```

## Arquitetura

### Sidecar JSON (gravado em `models/` ao iniciar /api/colab/start)
```json
{
  "slug":            "direito-tributario_llama-3.2-3b_20260306-1432",
  "topic":           "Direito Tributário",
  "subtopics":       ["ICMS", "ISS", "ITR"],
  "base_model":      "llama-3.2-3b",
  "quant_type":      "q4_k_m",
  "training_target": "colab",
  "created_at":      "2026-03-06T14:32:00"
}
```

### Backend changes

**`services/colab_manager.py`**
- `generate_notebook(model_id, topic_profile, params)` → recebe `model_slug` ou deriva internamente
- Helper `_make_slug(topic_area, model_id) -> str` — sanitiza e trunca
- Notebook salva GGUF como `{model_slug}.gguf` (não mais `modelo_final.gguf`)
- `generate_local_script()` idem

**`services/llama_cpp_runner.py`**
- `find_gguf_models()` → lê sidecar `.json` para cada `.gguf`; retorna campo `metadata` enriquecido
- Estrutura de retorno:
  ```python
  {
    "name": "direito-tributario_llama-3.2-3b_20260306-1432.gguf",
    "path": "/…/models/direito-tributario….gguf",
    "size_gb": 2.1,
    "topic": "Direito Tributário",
    "base_model": "llama-3.2-3b",
    "quant_type": "q4_k_m",
    "training_target": "colab",
    "created_at": "2026-03-06T14:32:00",
  }
  ```

**`routers/colab.py`**
- Ao determinar slug, grava imediatamente `models/{slug}.json` antes de iniciar background task
- Passa `model_slug` para `generate_notebook()` e `generate_local_script()`

### Frontend changes

**`10_Dashboard.tsx`**
- Cards de modelo mostram topic, base_model, quant_type, created_at (via metadata)
- Layout:
  ```
  ● Direito Tributário              [Ativo]
    llama-3.2-3b · Q4_K_M · 2.1 GB
    Colab T4 · 06/03/2026
  ```
- Botão "Treinar Novo Especialista" → `navigate('/settings')` + `resetWizard()` no WizardContext

**`WizardContext.tsx`**
- Adicionar função `resetWizard()` que restaura `defaultState`

## Fluxo de dados

```
/api/colab/start
  → deriva model_slug (topic_area + model_id + timestamp)
  → grava models/{slug}.json (sidecar)
  → generate_notebook(slug) ou generate_local_script(slug)
     (output GGUF = {slug}.gguf)

/api/training/status
  → find_gguf_models() lê *.gguf + sidecar *.json
  → retorna lista enriquecida

Dashboard seleciona especialista → /api/training/load
  → llama-server sobe com {slug}.gguf
```

## Arquivos a modificar/criar
- Modify: `backend/services/colab_manager.py`
- Modify: `backend/services/llama_cpp_runner.py`
- Modify: `backend/routers/colab.py`
- Modify: `frontend/src/pages/10_Dashboard.tsx`
- Modify: `frontend/src/context/WizardContext.tsx`
