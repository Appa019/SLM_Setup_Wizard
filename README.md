# Modelo SLM Local

Aplicacao full-stack wizard para fine-tuning de LLMs locais.

## Stack

- **Frontend:** React (Vite) + Tailwind CSS
- **Backend:** Python FastAPI
- **AI:** GPT-4o-mini (chat/preprocessing/recommendations) + GPT-5.4 (hyperparams via Responses API)
- **Treinamento:** Google Colab free tier (LoRA/QLoRA) ou GPU local se VRAM > 15GB
- **Runtime:** llama.cpp local
- **Scraping:** 1000-10000 URLs com anti-CAPTCHA (40 UAs, rate limiting, Playwright fallback)

## Comandos

```bash
# Backend
cd backend && source ../.venv/bin/activate && uvicorn main:app --reload

# Frontend
cd frontend && npm run dev
```

## Contributors

- [Appa019](https://github.com/Appa019)
