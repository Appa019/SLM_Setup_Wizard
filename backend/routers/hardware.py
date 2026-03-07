from fastapi import APIRouter
from services.hardware_scanner import scan

router = APIRouter()


@router.get("/scan")
async def scan_hardware():
    return scan()
