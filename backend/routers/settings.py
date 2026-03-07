from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.settings_service import save_openai_key, get_status, validate_openai_key

router = APIRouter()


class OpenAIKeyRequest(BaseModel):
    api_key: str


class GoogleEmailRequest(BaseModel):
    email: str


@router.post("/openai-key")
async def set_openai_key(body: OpenAIKeyRequest):
    if not body.api_key.startswith("sk-"):
        raise HTTPException(status_code=400, detail="Chave invalida: deve comecar com sk-")
    valid = await validate_openai_key(body.api_key)
    if not valid:
        raise HTTPException(status_code=401, detail="Chave OpenAI invalida ou sem creditos")
    save_openai_key(body.api_key)
    return {"ok": True, "message": "Chave salva e validada com sucesso"}


@router.post("/google-email")
async def set_google_email(body: GoogleEmailRequest):
    from utils.storage import write_env
    write_env({"GOOGLE_EMAIL": body.email})
    return {"ok": True}


@router.get("/status")
async def get_settings_status():
    return get_status()
