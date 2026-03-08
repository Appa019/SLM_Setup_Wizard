# Modelo SLM Local

Wizard completo de 10 etapas para criar **modelos de linguagem especializados** — do zero ao chat funcionando.

Voce define o tema, o sistema coleta dados da web, gera pares de treinamento com GPT-4o-mini, calcula hiperparametros otimos com GPT-5.1, treina via LoRA/QLoRA no Google Colab (T4 free) ou na sua GPU local, e entrega um modelo GGUF rodando localmente via llama.cpp.

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Frontend | React 19 · Vite 7 · TypeScript · Tailwind CSS 3 |
| Backend | Python 3.12 · FastAPI · Uvicorn |
| IA | GPT-4o-mini (chat, preprocessing, recomendacoes) · GPT-5.1 (hiperparametros via Responses API) |
| Scraping | httpx + BeautifulSoup · 40 User-Agents rotacionados · rate limiting por dominio · fallback Playwright |
| Treinamento | LoRA/QLoRA no Google Colab (T4 free) ou GPU local (VRAM > 15 GB) |
| Inferencia | llama.cpp local com modelo GGUF |

---

## Fluxo do Wizard

```
 01 Configuracoes       Credenciais OpenAI + conta Google
 02 Hardware Scan       Deteccao automatica de CPU, RAM, GPU, disco
 03 Modelo              GPT-5.1 recomenda modelos + variantes de quantizacao para o seu hardware
 04 Tema                Chat interativo para definir a area de especializacao
 05 Config Scraping     Escolha de volume (1k-10k URLs) e tipos de fonte
 06 Scraping            Coleta em tempo real com progresso SSE
 07 Pre-processamento   GPT-4o-mini transforma textos em pares instrucao/resposta (JSONL)
 08 Colab/GPU           GPT-5.1 gera hiperparametros otimos; notebook ou script gerado automaticamente
 09 Treinamento         Monitoramento ao vivo com metricas (epoch, loss, steps)
 10 Dashboard           Carrega modelo GGUF no llama.cpp e abre chat de teste
```

---

## Inicio Rapido

### Pre-requisitos

- Python 3.10+
- Node.js 18+
- Chave de API OpenAI (com creditos pay-as-you-go)
- Conta Google (para Colab)

### Instalacao

```bash
# Clonar
git clone git@github.com:Appa019/Modelo_SLM_Local.git
cd Modelo_SLM_Local

# Backend
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Frontend
cd frontend
npm install
cd ..
```

### Configuracao

Crie um arquivo `.env` na raiz:

```env
OPENAI_API_KEY=sk-proj-...
GOOGLE_EMAIL=seu@gmail.com   # opcional, apenas referencia
```

### Executar

```bash
# Terminal 1 — Backend
cd backend && source ../.venv/bin/activate && uvicorn main:app --reload

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Acesse **http://localhost:5173** e siga as 10 etapas do wizard.

---

## Arquitetura

```
├── backend/
│   ├── main.py                    FastAPI app + CORS + routers
│   ├── config.py                  Settings singleton (dotenv)
│   ├── routers/                   Um arquivo por dominio
│   │   ├── settings.py            Validacao de chave OpenAI
│   │   ├── hardware.py            Scan de CPU/RAM/GPU/disco
│   │   ├── models.py              Recomendacao de modelos (GPT-5.1)
│   │   ├── chat.py                Chat streaming para definicao de tema
│   │   ├── scraping.py            Controle + SSE de progresso
│   │   ├── preprocessing.py       Controle + SSE de progresso
│   │   ├── colab.py               Decisao local vs Colab + geracao
│   │   ├── training.py            Load/stop/chat com modelo GGUF
│   │   └── costs.py               Historico e estimativas de custo
│   └── services/                  Logica de negocio
│       ├── scraper.py             40 UAs, backoff, DuckDuckGo, Playwright fallback
│       ├── preprocessor.py        Chunking + GPT-4o-mini → JSONL
│       ├── hyperparams.py         GPT-5.1 Responses API (Dr. Alex Chen)
│       ├── model_recommender.py   Modelos + variantes de quantizacao
│       ├── colab_manager.py       Gera notebook .ipynb ou script .py
│       ├── colab_playwright.py    Automacao Chrome real via CDP
│       ├── cost_tracker.py        Registro de custos em costs.jsonl
│       ├── topic_chat.py          Chat streaming com GPT-4o-mini
│       └── llama_cpp_runner.py    Servidor llama.cpp local
│
├── frontend/
│   ├── src/
│   │   ├── pages/                 01-10 paginas do wizard
│   │   ├── components/            Layout, Stepper, ChatMessage, Loader, CostPanel
│   │   ├── context/               WizardContext (estado global)
│   │   ├── hooks/                 useApi
│   │   └── lib/                   api.ts (axios)
│   └── public/                    Logo + 10 icones do stepper
│
├── data/                          Gerado em runtime
│   ├── raw/                       HTML bruto do scraping
│   ├── processed/                 training_data.jsonl
│   └── costs.jsonl                Log de custos OpenAI
│
├── colab/                         Notebooks/scripts gerados
└── models/                        Modelos GGUF treinados
```

### Decisao GPU Local vs Colab

Logica deterministica — nao depende do GPT-5.1:

- **VRAM do usuario > 15 GB** → treinamento local (`colab/local_training.py`)
- **Caso contrario** → Google Colab T4 free (`colab/generated_notebook.ipynb` + automacao Playwright)

O GPT-5.1 otimiza `lora_r`, `batch_size`, `learning_rate` etc., mas o backend sempre sobrescreve `training_target`.

### Automacao Colab

Chrome real lancado via `subprocess.Popen()` sem flags de automacao. Playwright conecta via CDP (`localhost:9222`). Perfil persistente em `.colab-profile/` para manter login entre sessoes. UI em PT-BR.

---

## Design

Interface **Industrial Tech Dashboard** — estetica clean tech inspirada em Linear e Vercel Dashboard.

- **Tipografia**: Space Mono para titulos/labels, Inter para corpo, JetBrains Mono para dados
- **Geometria**: Bordas sharp (1px max), zero arredondamento visivel
- **Componentes**: Botoes uppercase, badges industriais, terminal-box para logs, cards com accent borders
- **Icones**: 10 icones PNG customizados no stepper + logo real

---

## API Endpoints

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/api/settings/status` | Status das credenciais |
| POST | `/api/settings/openai-key` | Validar e salvar chave OpenAI |
| GET | `/api/hardware/scan` | Scan completo de hardware |
| POST | `/api/models/recommendations` | Modelos recomendados pelo GPT-5.1 |
| POST | `/api/chat/message` | Chat streaming (definicao de tema) |
| POST | `/api/chat/finalize` | Extrair perfil do tema |
| POST | `/api/scraping/config` | Configurar scraping |
| POST | `/api/scraping/start` | Iniciar scraping |
| GET | `/api/scraping/status` | SSE — progresso do scraping |
| POST | `/api/preprocessing/start` | Iniciar pre-processamento |
| GET | `/api/preprocessing/status` | SSE — progresso do pre-processamento |
| POST | `/api/colab/start` | Gerar hiperparametros + notebook/script |
| GET | `/api/colab/status` | SSE — progresso do treinamento |
| POST | `/api/training/load` | Carregar modelo GGUF no llama.cpp |
| POST | `/api/training/chat` | Chat com modelo treinado |
| GET | `/api/costs/estimate` | Custos acumulados + estimativa |
| GET | `/api/costs/history` | Historico de chamadas OpenAI |

---

## Custos

Painel de custos em tempo real integrado no frontend (canto inferior direito). Toda chamada OpenAI e registrada automaticamente.

Modelos usados e custos tipicos por sessao completa (1k URLs):

| Fase | Modelo | Custo estimado |
|------|--------|---------------|
| Recomendacao de modelos | GPT-5.1 | ~$0.05 |
| Chat de tema (3-5 trocas) | GPT-4o-mini | ~$0.002 |
| Pre-processamento (1k chunks) | GPT-4o-mini | ~$0.15 |
| Hiperparametros | GPT-5.1 | ~$0.08 |
| **Total** | | **~$0.30** |

---

## Desenvolvimento

```bash
# Build de producao
cd frontend && npm run build

# Smoke test do backend
cd backend && timeout 6 uvicorn main:app --host 127.0.0.1 --port 8000
# exit 143 = OK (processo morto pelo timeout)
```

Nao ha framework de testes automatizados. Testes da automacao Colab sao scripts standalone em `colab/tests/t1-t5`.

---

## Licenca

Projeto privado.

## Autor

[Appa019](https://github.com/Appa019)
