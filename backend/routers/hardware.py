from fastapi import APIRouter

router = APIRouter()


@router.get("/scan")
async def scan_hardware():
    return {"status": "not_implemented"}
