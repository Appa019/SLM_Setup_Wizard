from fastapi import APIRouter

router = APIRouter()


@router.post("/start")
async def start_preprocessing():
    return {"status": "not_implemented"}
