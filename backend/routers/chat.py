from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services.topic_chat import stream_chat, finalize_topic
from config import settings

router = APIRouter()


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


@router.post("/message")
async def send_message(body: ChatRequest):
    if not settings.openai_api_key:
        raise HTTPException(status_code=400, detail="Configure a OpenAI API Key primeiro")

    messages = [m.model_dump() for m in body.messages]

    async def generator():
        async for chunk in stream_chat(messages):
            yield chunk

    return StreamingResponse(generator(), media_type="text/plain")


@router.post("/finalize")
async def finalize_chat(body: ChatRequest):
    if not settings.openai_api_key:
        raise HTTPException(status_code=400, detail="Configure a OpenAI API Key primeiro")
    messages = [m.model_dump() for m in body.messages]
    profile = await finalize_topic(messages)
    return {"profile": profile}
