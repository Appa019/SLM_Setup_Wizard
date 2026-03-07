from fastapi import APIRouter

router = APIRouter()


@router.post("/start")
async def start_scraping():
    return {"status": "not_implemented"}
