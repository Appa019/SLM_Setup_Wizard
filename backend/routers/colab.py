from fastapi import APIRouter

router = APIRouter()


@router.post("/start")
async def start_colab():
    return {"status": "not_implemented"}
