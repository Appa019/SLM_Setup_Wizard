import json
import time
from pathlib import Path

COSTS_FILE = Path(__file__).parent.parent.parent / "data" / "costs.jsonl"

# Precos OpenAI 2026 (USD por 1M tokens)
PRICING: dict[str, dict[str, float]] = {
    "gpt-5.4":       {"in": 7.50,  "out": 30.00},
    "gpt-5.4-pro":   {"in": 15.00, "out": 60.00},
    "gpt-5.2":       {"in": 3.50,  "out": 14.00},
    "gpt-4o":        {"in": 2.50,  "out": 10.00},
    "gpt-4o-mini":   {"in": 0.15,  "out": 0.60},
    "gpt-4.1":       {"in": 2.00,  "out": 8.00},
    "gpt-4.1-mini":  {"in": 0.40,  "out": 1.60},
    "gpt-4.1-nano":  {"in": 0.10,  "out": 0.40},
    "o4-mini":       {"in": 1.10,  "out": 4.40},
    "o3":            {"in": 10.00, "out": 40.00},
}

PHASE_LABELS = {
    "recommendation":       "Recomendacao de modelo",
    "model_recommendation": "Recomendacao de modelo",
    "chat":                 "Chat de tema",
    "preprocessing":        "Pre-processamento",
    "hyperparams":          "Hiperparametros (GPT-5.4)",
    "other":                "Outros",
}


def record(model: str, phase: str, tokens_in: int, tokens_out: int) -> dict:
    """Registra uma chamada OpenAI e calcula custo."""
    price = PRICING.get(model, {"in": 0.0, "out": 0.0})
    cost  = (tokens_in * price["in"] + tokens_out * price["out"]) / 1_000_000
    entry = {
        "ts":         time.time(),
        "model":      model,
        "phase":      phase,
        "tokens_in":  tokens_in,
        "tokens_out": tokens_out,
        "cost_usd":   round(cost, 6),
    }
    COSTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with COSTS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def get_history() -> list[dict]:
    if not COSTS_FILE.exists():
        return []
    entries = []
    for line in COSTS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
    return entries


def get_summary() -> dict:
    history  = get_history()
    total    = sum(e["cost_usd"] for e in history)
    by_phase: dict[str, float] = {}
    for e in history:
        by_phase[e["phase"]] = round(by_phase.get(e["phase"], 0) + e["cost_usd"], 6)
    return {"total_usd": round(total, 6), "by_phase": by_phase, "calls": len(history)}


def estimate_preprocessing(url_count: int, model: str = "gpt-4o-mini") -> float:
    """Estima custo de preprocessing baseado no volume de URLs."""
    avg_chunks_per_url = 2.5
    avg_tokens_in      = 800   # texto do chunk
    avg_tokens_out     = 300   # pares gerados
    total_chunks       = url_count * avg_chunks_per_url
    price              = PRICING.get(model, {"in": 0.15, "out": 0.60})
    cost = (total_chunks * avg_tokens_in * price["in"] +
            total_chunks * avg_tokens_out * price["out"]) / 1_000_000
    return round(cost, 4)
