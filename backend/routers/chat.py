from fastapi import APIRouter

router = APIRouter()


@router.post("/message")
async def send_message():
    return {"status": "not_implemented"}
