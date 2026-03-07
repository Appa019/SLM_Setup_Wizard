# CLAUDE.md - Modelo SLM Local

## Projeto
Aplicacao full-stack wizard para fine-tuning de LLMs locais.
- Frontend: React (Vite) + Tailwind CSS
- Backend: Python FastAPI
- AI: OpenAI API (GPT-4o) para chatbot, recomendacoes e pre-processamento
- Treinamento: Google Colab free tier (LoRA/QLoRA)
- Runtime: llama.cpp local
- Scraping: 1000-10000 URLs

## Regras
- Atualizar memoria com frequencia (padroes, decisoes, progresso)
- Deploy ao GitHub apos mudancas importantes
- Nenhum commit deve ser co-autorado por Claude ou citar Claude
- Remote SSH: git@github.com:Appa019/Modelo_SLM_Local.git

## Comandos
- Backend: `cd backend && uvicorn main:app --reload`
- Frontend: `cd frontend && npm run dev`

## Estrutura
- `/backend` - FastAPI com routers/ e services/
- `/frontend` - React Vite com pages/ seguindo wizard steps 01-10
- `/colab` - Template notebooks para treinamento
