import asyncio
import json
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services.colab_manager import generate_notebook, generate_local_script
from services.colab_playwright import run_colab_automation, get_training_state
from services.hyperparams import generate_hyperparams

router = APIRouter()

PROJECT_ROOT   = Path(__file__).parent.parent.parent
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
MODELS_DIR     = PROJECT_ROOT / "models"


class ColabStartRequest(BaseModel):
    model_id:      str  = "llama-3.2-3b"
    quant_type:    str  = "q4_k_m"
    topic_profile: dict = {}
    hardware:      dict = {}


@router.post("/generate-notebook")
async def generate_colab_notebook(body: ColabStartRequest):
    notebook_path = generate_notebook(body.model_id, body.topic_profile)
    return {
        "ok": True,
        "notebook_path": str(notebook_path),
        "message": f"Notebook gerado em {notebook_path.name}",
    }


@router.post("/start")
async def start_colab(body: ColabStartRequest, background_tasks: BackgroundTasks):
    state = get_training_state()
    if state["running"]:
        raise HTTPException(status_code=409, detail="Automacao Colab ja em execucao")

    dataset_path = DATA_PROCESSED / "training_data.jsonl"
    if not dataset_path.exists():
        raise HTTPException(status_code=400, detail="Execute o pre-processamento primeiro")

    # Estimar pares de dataset para contexto dos hiperparametros
    try:
        with dataset_path.open(encoding="utf-8") as f:
            dataset_pairs = sum(1 for line in f if line.strip())
    except Exception:
        dataset_pairs = 2000

    # Gerar hiperparametros otimos via GPT-5.4
    params = await generate_hyperparams(
        model_id=body.model_id,
        quant_type=body.quant_type,
        hardware=body.hardware,
        dataset_pairs=dataset_pairs,
    )

    training_target = params.get("training_target", "colab")

    # Se GPU do usuario for superior ao T4 → script local
    if training_target == "local":
        script_path = generate_local_script(body.model_id, body.topic_profile, params)
        return {
            "ok":          True,
            "target":      "local",
            "script_path": str(script_path),
            "params":      params,
        }

    # Caso contrario → notebook Colab + automacao Playwright
    notebook_path = generate_notebook(body.model_id, body.topic_profile, params)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    background_tasks.add_task(run_colab_automation, notebook_path, dataset_path, MODELS_DIR)
    return {
        "ok":            True,
        "target":        "colab",
        "notebook_path": str(notebook_path),
        "params":        params,
    }


@router.get("/status")
async def stream_colab_status():
    async def event_stream():
        while True:
            state = get_training_state()
            yield f"data: {json.dumps(state)}\n\n"
            if state["finished"] or state["error"]:
                break
            await asyncio.sleep(1)
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/state")
async def get_colab_state():
    return get_training_state()
