import asyncio
import json
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services.scraper import run_scraping, get_state

router = APIRouter()

_scraping_config: dict = {}


class ScrapingConfig(BaseModel):
    url_count: int = 1000
    topic_profile: dict = {}


@router.post("/config")
async def save_config(body: ScrapingConfig):
    global _scraping_config
    _scraping_config = body.model_dump()
    return {"ok": True}


@router.post("/start")
async def start_scraping(background_tasks: BackgroundTasks):
    state = get_state()
    if state["running"]:
        raise HTTPException(status_code=409, detail="Scraping ja em execucao")
    if not _scraping_config:
        raise HTTPException(status_code=400, detail="Configure o scraping primeiro")
    background_tasks.add_task(
        run_scraping,
        _scraping_config.get("topic_profile", {}),
        _scraping_config.get("url_count", 1000),
    )
    return {"ok": True, "message": "Scraping iniciado"}


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
async def get_scraping_state():
    return get_state()
