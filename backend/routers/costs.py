from fastapi import APIRouter
from services.cost_tracker import get_history, get_summary, estimate_preprocessing, PHASE_LABELS

router = APIRouter()


@router.get("/history")
async def history():
    return get_history()


@router.get("/summary")
async def summary():
    return get_summary()


@router.get("/estimate")
async def estimate(url_count: int = 1000, model: str = "gpt-4o-mini"):
    preproc = estimate_preprocessing(url_count, model)
    s = get_summary()
    return {
        "accumulated_usd":           s["total_usd"],
        "preprocessing_estimate_usd": preproc,
        "total_estimate_usd":        round(s["total_usd"] + preproc, 4),
        "phase_labels":              PHASE_LABELS,
        "by_phase":                  s["by_phase"],
    }
