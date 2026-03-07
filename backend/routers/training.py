from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def get_training_status():
    return {"status": "not_implemented"}
