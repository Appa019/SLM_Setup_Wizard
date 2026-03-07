from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.model_recommender import get_recommendations
from config import settings

router = APIRouter()


class HardwarePayload(BaseModel):
    ram_gb: float = 8.0
    vram_gb: float | None = None
    gpu: str | None = None


@router.post("/recommendations")
async def recommend_models(hardware: HardwarePayload):
    if not settings.openai_api_key:
        raise HTTPException(status_code=400, detail="Configure a OpenAI API Key primeiro")
    recs = await get_recommendations(hardware.model_dump())
    return {"recommendations": recs}
