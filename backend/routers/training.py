from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.llama_cpp_runner import get_status, load_model, stop_model, chat_with_model

router = APIRouter()


class LoadModelRequest(BaseModel):
    model_name: str


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@router.get("/status")
async def get_model_status():
    return get_status()


@router.post("/load")
async def load(body: LoadModelRequest):
    result = await load_model(body.model_name)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/stop")
async def stop():
    await stop_model()
    return {"ok": True}


@router.post("/chat")
async def chat(body: ChatRequest):
    response = await chat_with_model(body.message, body.history)
    return {"response": response}
