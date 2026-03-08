# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projeto
Aplicacao full-stack wizard (10 passos) para fine-tuning de LLMs locais com treinamento via Google Colab ou GPU local.
- Frontend: React + Vite + TypeScript + Tailwind CSS v3
- Backend: Python FastAPI (uvicorn)
- AI: GPT-4o-mini (chat/preprocessing/recommendations) + GPT-5.1 (hyperparams via Responses API)
- Treinamento: LoRA/QLoRA no Google Colab (T4 free) ou GPU local se VRAM > 15GB
- Runtime: llama.cpp local
- Scraping: httpx + BeautifulSoup com 40 UAs rotacionados, rate limiting por dominio, fallback Playwright

## Comandos
```bash
# Backend (rodar da raiz)
cd backend && source ../.venv/bin/activate && uvicorn main:app --reload

# Frontend
cd frontend && npm run dev

# Build frontend
cd frontend && npm run build

# Testar startup backend (exit 143 = OK, processo morto pelo timeout)
timeout 6 uvicorn main:app --host 127.0.0.1 --port 8000
```

## Arquitetura

### Fluxo Wizard (frontend)
10 paginas sequenciais em `frontend/src/pages/01-10_*.tsx`. Estado global em `WizardContext.tsx` (React Context + `useState`). Rotas em `App.tsx`:
```
/settings → /hardware → /model → /topic → /scraping/config → /scraping/progress → /preprocessing → /colab → /training → /dashboard
```

### Backend API (`backend/`)
- `main.py` — monta todos os routers com prefixo `/api/*`; CORS permitido apenas em `localhost:5173`
- `config.py` — `Settings` singleton; le `OPENAI_API_KEY` e `GOOGLE_EMAIL` do `os.environ` (dotenv carregado no startup)
- `routers/` — um arquivo por dominio: settings, hardware, models, chat, scraping, preprocessing, colab, training, costs
- `services/` — logica de negocio desacoplada dos routers

### Servicos principais
| Servico | Funcao |
|---------|--------|
| `scraper.py` | Scraping assincrono; `scraping_state` dict em memoria; SSE via `/api/scraping/status` |
| `preprocessor.py` | Gera pares instrucao/resposta (JSONL) usando GPT-4o-mini; SSE via `/api/preprocessing/status` |
| `hyperparams.py` | GPT-5.1 Responses API com prompt "Dr. Alex Chen"; retorna hiperparametros otimos de LoRA |
| `colab_manager.py` | Gera `colab/generated_notebook.ipynb` ou `colab/local_training.py` |
| `colab_playwright.py` | Automacao completa do Colab: Chrome real (subprocess+CDP) com login persistente, upload, T4 GPU, run all, download .gguf |
| `model_recommender.py` | Lista modelos com variantes de quantizacao (full/Q8/Q4_K_M) e VRAM necessaria |
| `cost_tracker.py` | Registra cada chamada OpenAI em `data/costs.jsonl`; calcula custo em USD |
| `llama_cpp_runner.py` | Executa modelo GGUF localmente via llama.cpp |

### SSE (Server-Sent Events)
Usado em tres routers para progresso em tempo real. O frontend fecha a conexao quando recebe `d.finished || d.error`. Ao adicionar novo SSE no backend, seguir o padrao de `scraping.py`: estado em dict em memoria, `asyncio.sleep(1)` entre eventos, break ao finalizar.

### Logica GPU local vs Colab
**Decisao deterministica em `routers/colab.py`** — nao depende do GPT-5.1:
```python
T4_VRAM_GB = 15.0  # importado de services/hyperparams.py
user_vram = body.hardware.get("vram_gb") or 0.0
params["training_target"] = "local" if user_vram > T4_VRAM_GB else "colab"
```
GPT-5.1 otimiza `lora_r`, `batch_size`, etc., mas o router SEMPRE sobrescreve `training_target`.
- `training_target="local"` → `colab/local_training.py` + `requirements.txt`
- `training_target="colab"` → `colab/generated_notebook.ipynb` + automacao Playwright

### Automacao Colab (Chrome + CDP)
Chrome real lancado via `subprocess.Popen()` SEM flags de automacao (`--enable-automation` bloquearia login Google). Playwright conecta via `p.chromium.connect_over_cdp("http://localhost:9222")`.
- **Perfil persistente**: `.colab-profile/` salva cookies/login entre sessoes (adicionado ao `.gitignore`)
- **UI PT-BR**: seletores usam texto em portugues — `Arquivo`, `Fazer upload de notebook`, `Ambiente de execucao`, `Alterar tipo de ambiente de execucao`
- **Shadow DOM**: botoes Material Design 3 (ex: salvar GPU) precisam de `get_by_role("button").all()`, nao `button:has-text()`
- **Radio buttons**: DEVE usar `page.click()` (mouse real), nao `page.evaluate(el.click())` — radio nao dispara change event com click programatico
- **Download .gguf**: configurado via `Browser.setDownloadBehavior` (CDP session), NAO chamar `download.save_as()` (Chrome real nao suporta)
- **Testes manuais**: `colab/tests/t1_connect.py` a `t5_download.py` — scripts standalone, rodar individualmente

### Frontend
- `frontend/src/lib/api.ts` — instancia axios com `baseURL=http://localhost:8000` e timeout 180s (GPT-5.1 reasoning demora)
- `frontend/src/hooks/useApi.ts` — hook generico para chamadas REST
- `frontend/src/components/CostPanel.tsx` — painel flutuante bottom-right, polling 10s em `/api/costs/summary`; montado no `Layout.tsx`
- Tema CSS: classes `surface-50/100/200/300` + `accent-400/500/600` + `teal-400/500/600`

### Design System — Industrial Tech Dashboard
Estetica clean tech inspirada em Linear/Vercel Dashboard. Tema claro, sem dark mode global.
- **Fontes**: Inter (body), Space Mono (display/titles/labels/badges via `font-display`), JetBrains Mono (`font-mono`)
- **Bordas**: Praticamente zero border-radius — DEFAULT 1px, sm 0px, md 2px, lg 3px. Zero `rounded-full`
- **Botoes**: `uppercase tracking-wide text-[11px] font-semibold` — estilo controle de painel
- **Badges**: `uppercase tracking-wider text-[10px] font-bold` — tags industriais quadradas
- **Section titles**: `font-display text-[10px] font-bold uppercase tracking-[0.08em]` (classe `.section-title`)
- **Cards**: Sharp edges, suporte a `border-l-2` e `border-t-2` accent para destaque
- **Terminal**: `.terminal-box` — bg-gray-950, mono green, para logs e previews de dados
- **Data display**: `.data-label` (Space Mono 10px uppercase) + `.data-value` (mono semibold)
- **Range slider**: Thumb quadrado (#3d63ae), track 4px, sem border-radius
- **Icones**: PNGs em `frontend/public/01-10_icone.png` para steps do wizard + `logo.png` para branding
- **Sidebar**: bg-white, w-56, dot-grid-light texture, steps com `border-l-2` active state e icones PNG
- **Loader**: Scanning line horizontal varrendo dentro de quadrado (nao spinner)
- **Shadows**: Sutis e tight — `card: 0 1px 2px`, `card-md: 0 1px 4px`

## Padroes de codigo

### OpenAI Responses API (GPT-5.1)
```python
response = await client.responses.create(
    model="gpt-5.1",
    reasoning={"effort": "high"},
    store=True,
    input=[...]
)
# Iterar output:
for item in response.output:
    if item.type == "message":
        for block in item.content:
            if block.type == "output_text":
                text = block.text
# Tokens (nao usar prompt_tokens):
tokens_in = getattr(usage, "input_tokens", 0)
```

### Cost tracking (obrigatorio em toda chamada OpenAI)
```python
from services import cost_tracker
cost_tracker.record(model, phase, tokens_in, tokens_out)
```
Fases validas: `"recommendation"`, `"model_recommendation"`, `"chat"`, `"preprocessing"`, `"hyperparams"`, `"other"`.

### TypeScript / React
- `verbatimModuleSyntax: true` — usar `import type` para tipos (ex: `import type { ReactNode } from 'react'`)
- `useCallback(fn, [])` para funcoes estabilizadas no contexto (ex: `update`, `resetWizard` em WizardContext)
- SSE nos componentes: fechar EventSource quando `d.finished || d.error`; deps do `useEffect` que abre SSE devem ser `[]`
- Preprocessing `max_tokens=1100`

## Regras
- Nenhum commit deve ser co-autorado por Claude ou citar Claude
- Remote SSH: `git@github.com:Appa019/Modelo_SLM_Local.git`
- Deploy ao GitHub apos mudancas importantes
- Atualizar memoria com frequencia (padroes, decisoes, progresso)
- `Write` em arquivo existente requer `Read` primeiro, mesmo que parcial

## Testes
Nao ha framework de testes (pytest/vitest). Testes Colab sao scripts standalone em `colab/tests/t1-t5` — rodar manualmente. Smoke test backend: `timeout 6 uvicorn main:app --host 127.0.0.1 --port 8000` (exit 143 = OK).

## Dados gerados em runtime
- `data/raw/` — HTML bruto do scraping
- `data/processed/training_data.jsonl` — pares instrucao/resposta apos preprocessing
- `data/costs.jsonl` — log append-only de todas as chamadas OpenAI
- `colab/` — notebook/script gerados dinamicamente; nao commitar
- `models/` — modelos GGUF baixados do Colab; nao commitar
