import asyncio
import json
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services.preprocessor import run_preprocessing, get_state
from config import settings

router = APIRouter()


class PreprocessRequest(BaseModel):
    topic_profile: dict = {}


@router.post("/start")
async def start_preprocessing(body: PreprocessRequest, background_tasks: BackgroundTasks):
    if not settings.openai_api_key:
        raise HTTPException(status_code=400, detail="Configure a OpenAI API Key primeiro")
    state = get_state()
    if state["running"]:
        raise HTTPException(status_code=409, detail="Preprocessing ja em execucao")
    background_tasks.add_task(run_preprocessing, body.topic_profile)
    return {"ok": True}


@router.get("/status")
async def stream_status():
    async def event_stream():
        while True:
            state = get_state()
            yield f"data: {json.dumps(state)}\n\n"
            if state["finished"] or state["error"]:
                break
            await asyncio.sleep(1)
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/state")
async def get_preprocessing_state():
    return get_state()
