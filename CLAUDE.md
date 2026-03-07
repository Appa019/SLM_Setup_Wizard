# CLAUDE.md - Modelo SLM Local

## Projeto
Aplicacao full-stack wizard para fine-tuning de LLMs locais.
- Frontend: React (Vite) + Tailwind CSS
- Backend: Python FastAPI
- AI: GPT-4o-mini (chat/preprocessing/recommendations) + GPT-5.4 (hyperparams via Responses API)
- Treinamento: Google Colab free tier (LoRA/QLoRA) ou GPU local se user_vram > 15GB
- Runtime: llama.cpp local
- Scraping: 1000-10000 URLs com anti-CAPTCHA (40 UAs, rate limiting, Playwright fallback)

## Regras
- Atualizar memoria com frequencia (padroes, decisoes, progresso)
- Deploy ao GitHub apos mudancas importantes
- Nenhum commit deve ser co-autorado por Claude ou citar Claude
- Remote SSH: git@github.com:Appa019/Modelo_SLM_Local.git

## Logica GPU local vs Colab
- user_vram > 15GB (T4) → gera `colab/local_training.py` + `requirements.txt`
- user_vram <= 15GB ou sem GPU → gera `colab/generated_notebook.ipynb` + automacao Playwright
- Decisao feita em `services/hyperparams.py` via GPT-5.4; fallback em `_conservative_defaults()`

## Comandos
- Backend: `cd backend && source ../.venv/bin/activate && uvicorn main:app --reload`
- Frontend: `cd frontend && npm run dev`
- Build frontend: `cd frontend && npm run build`
- Testar startup backend (exit 143 = OK): `timeout 6 uvicorn main:app --host 127.0.0.1 --port 8000`

## Padroes de codigo
- GPT-5.4 Responses API: `client.responses.create(model="gpt-5.4", reasoning={"effort":"high"}, store=True, input=[...])`
- Responses API output: iterar `response.output`, checar `item.type=="message"` → `block.type=="output_text"` → `block.text`
- Responses API tokens: `getattr(usage, "input_tokens", 0)` (nao `prompt_tokens`)
- Toda chamada OpenAI deve chamar `cost_tracker.record(model, phase, tokens_in, tokens_out)` apos a resposta
- Preprocessing `max_tokens=1100`
- Write tool em arquivo existente requer Read primeiro, mesmo que parcial

## Servicos V2 adicionados
- `services/cost_tracker.py` — PRICING 2026, record(), get_history(), estimate_preprocessing()
- `services/hyperparams.py` — GPT-5.4 + Dr Alex Chen prompt, gera hiperparametros + training_target
- `services/model_recommender.py` — cada modelo tem `quant_options` (full/q8/q4_k_m) com VRAM e compat
- `routers/costs.py` — GET /api/costs/history, /summary, /estimate
- `components/CostPanel.tsx` — montado em Layout, polling 10s, botao flutuante bottom-right

## Estrutura
- `/backend` - FastAPI com routers/ e services/
- `/frontend` - React Vite com pages/ seguindo wizard steps 01-10
- `/colab` - Notebooks e scripts gerados dinamicamente pela IA
- `/data/costs.jsonl` — append log de todas as chamadas OpenAI
