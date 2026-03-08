# Design: Colab — Abrir no Browser Padrão do Sistema

**Data:** 2026-03-08

## Problema

`colab_playwright.py` usa Playwright/Chromium para abrir o Google Colab. O Google detecta o browser automatizado como inseguro e bloqueia o login — tornando a automação inutilizável.

## Solução

Substituir a automação Playwright por `webbrowser.open()` (biblioteca padrão Python). O sistema:
1. Abre o Colab no browser real do usuário (Chrome/Firefox/Edge — o que estiver instalado)
2. Exibe instruções passo-a-passo no log do frontend (`09_Training.tsx`)
3. Monitora `models/` a cada 10s aguardando um arquivo `.gguf` aparecer
4. Quando detecta o `.gguf` → marca `training_state["finished"] = True`

## Interface (sem mudanças)

- `training_state` dict: inalterado
- SSE `/api/colab/status`: inalterado
- `run_colab_automation(notebook_path, dataset_path, model_out_dir)`: mesma assinatura
- Router `routers/colab.py`: sem alterações
- Frontend: sem alterações

## Arquivo modificado

Apenas `backend/services/colab_playwright.py` — reescrita do corpo de `run_colab_automation()`.
