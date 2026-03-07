import json
from utils.openai_client import get_openai_client

CANDIDATE_MODELS = [
    {
        "id": "llama-3.2-1b",
        "name": "LLaMA 3.2 1B",
        "params": "1B",
        "min_ram_gb": 2,
        "min_vram_gb": 1,
        "size_gb": 0.8,
        "description": "Modelo ultra-leve da Meta. Ideal para hardware limitado.",
    },
    {
        "id": "llama-3.2-3b",
        "name": "LLaMA 3.2 3B",
        "params": "3B",
        "min_ram_gb": 4,
        "min_vram_gb": 2,
        "size_gb": 2.0,
        "description": "Equilibrio entre tamanho e qualidade. Bom para a maioria dos casos.",
    },
    {
        "id": "phi-3-mini",
        "name": "Phi-3 Mini 3.8B",
        "params": "3.8B",
        "min_ram_gb": 4,
        "min_vram_gb": 2,
        "size_gb": 2.4,
        "description": "Modelo da Microsoft, excelente em raciocinio para seu tamanho.",
    },
    {
        "id": "mistral-7b",
        "name": "Mistral 7B",
        "params": "7B",
        "min_ram_gb": 8,
        "min_vram_gb": 6,
        "size_gb": 4.1,
        "description": "Referencia em qualidade para 7B. Excelente em instrucoes.",
    },
    {
        "id": "qwen2-7b",
        "name": "Qwen2 7B",
        "params": "7B",
        "min_ram_gb": 8,
        "min_vram_gb": 6,
        "size_gb": 4.4,
        "description": "Modelo da Alibaba, forte em multilingual e codigo.",
    },
]


def _compatibility(model: dict, ram_gb: float, vram_gb: float | None) -> str:
    effective = vram_gb if vram_gb else ram_gb * 0.5
    if effective >= model["min_vram_gb"] * 1.5:
        return "high"
    elif effective >= model["min_vram_gb"]:
        return "medium"
    else:
        return "low"


async def get_recommendations(hardware: dict) -> list[dict]:
    ram_gb = hardware.get("ram_gb", 8)
    vram_gb = hardware.get("vram_gb")

    # Add compatibility to each candidate
    candidates = []
    for m in CANDIDATE_MODELS:
        compat = _compatibility(m, ram_gb, vram_gb)
        candidates.append({**m, "compatibility": compat})

    # Use OpenAI to rank and enrich
    try:
        client = get_openai_client()
        hw_summary = f"RAM: {ram_gb}GB, GPU: {hardware.get('gpu', 'none')}, VRAM: {vram_gb}GB"
        prompt = f"""Hardware do usuario: {hw_summary}

Modelos candidatos: {json.dumps([c['name'] for c in candidates])}

Retorne JSON com array 'recommendations' contendo os 3-4 melhores modelos para esse hardware,
com campos: id, pros (lista de 2-3 itens), cons (lista de 1-2 itens), best_for (string curta).
Use apenas os IDs da lista: {[c['id'] for c in candidates]}"""

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=600,
        )
        enriched = json.loads(response.choices[0].message.content or "{}")
        recs = enriched.get("recommendations", [])

        # Merge OpenAI data with candidate data
        result = []
        for rec in recs:
            base = next((c for c in candidates if c["id"] == rec.get("id")), None)
            if base:
                result.append({**base, **rec})
        return result if result else candidates[:4]

    except Exception:
        return [c for c in candidates if c["compatibility"] != "low"][:4]
