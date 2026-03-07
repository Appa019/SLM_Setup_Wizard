import json
from utils.openai_client import get_openai_client
from services.cost_tracker import record

T4_VRAM = 15.0  # GB — Colab free tier

CANDIDATE_MODELS = [
    {
        "id": "llama-3.2-1b",
        "name": "LLaMA 3.2 1B",
        "params": "1B",
        "description": "Modelo ultra-leve da Meta. Ideal para hardware muito limitado.",
        "quant_options": [
            {"type": "full",   "label": "Full (FP16)",    "vram_gb": 2.5, "hf_id": "meta-llama/Llama-3.2-1B-Instruct"},
            {"type": "q8",     "label": "Q8_0 (8-bit)",   "vram_gb": 1.3, "hf_id": "meta-llama/Llama-3.2-1B-Instruct"},
            {"type": "q4_k_m", "label": "Q4_K_M (4-bit)", "vram_gb": 0.8, "hf_id": "meta-llama/Llama-3.2-1B-Instruct"},
        ],
    },
    {
        "id": "llama-3.2-3b",
        "name": "LLaMA 3.2 3B",
        "params": "3B",
        "description": "Equilibrio entre tamanho e qualidade. Boa escolha geral.",
        "quant_options": [
            {"type": "full",   "label": "Full (FP16)",    "vram_gb": 6.5, "hf_id": "meta-llama/Llama-3.2-3B-Instruct"},
            {"type": "q8",     "label": "Q8_0 (8-bit)",   "vram_gb": 3.5, "hf_id": "meta-llama/Llama-3.2-3B-Instruct"},
            {"type": "q4_k_m", "label": "Q4_K_M (4-bit)", "vram_gb": 2.0, "hf_id": "meta-llama/Llama-3.2-3B-Instruct"},
        ],
    },
    {
        "id": "phi-3-mini",
        "name": "Phi-3 Mini 3.8B",
        "params": "3.8B",
        "description": "Modelo da Microsoft, excelente em raciocinio para seu tamanho.",
        "quant_options": [
            {"type": "full",   "label": "Full (FP16)",    "vram_gb": 7.5, "hf_id": "microsoft/Phi-3-mini-4k-instruct"},
            {"type": "q8",     "label": "Q8_0 (8-bit)",   "vram_gb": 4.0, "hf_id": "microsoft/Phi-3-mini-4k-instruct"},
            {"type": "q4_k_m", "label": "Q4_K_M (4-bit)", "vram_gb": 2.4, "hf_id": "microsoft/Phi-3-mini-4k-instruct"},
        ],
    },
    {
        "id": "mistral-7b",
        "name": "Mistral 7B",
        "params": "7B",
        "description": "Referencia em qualidade 7B. Excelente em instrucoes e raciocinio.",
        "quant_options": [
            {"type": "full",   "label": "Full (FP16)",    "vram_gb": 14.5, "hf_id": "mistralai/Mistral-7B-Instruct-v0.3"},
            {"type": "q8",     "label": "Q8_0 (8-bit)",   "vram_gb": 8.0,  "hf_id": "mistralai/Mistral-7B-Instruct-v0.3"},
            {"type": "q4_k_m", "label": "Q4_K_M (4-bit)", "vram_gb": 4.5,  "hf_id": "mistralai/Mistral-7B-Instruct-v0.3"},
        ],
    },
    {
        "id": "qwen2-7b",
        "name": "Qwen2 7B",
        "params": "7B",
        "description": "Modelo da Alibaba, forte em multilingual e codigo.",
        "quant_options": [
            {"type": "full",   "label": "Full (FP16)",    "vram_gb": 15.0, "hf_id": "Qwen/Qwen2-7B-Instruct"},
            {"type": "q8",     "label": "Q8_0 (8-bit)",   "vram_gb": 8.5,  "hf_id": "Qwen/Qwen2-7B-Instruct"},
            {"type": "q4_k_m", "label": "Q4_K_M (4-bit)", "vram_gb": 4.8,  "hf_id": "Qwen/Qwen2-7B-Instruct"},
        ],
    },
]


def _compat(vram_needed: float, user_vram: float | None) -> str:
    """Compatibilidade baseada no melhor VRAM disponivel (user GPU vs T4)."""
    effective = max(user_vram or 0, T4_VRAM)
    if effective >= vram_needed * 1.4:
        return "high"
    if effective >= vram_needed:
        return "medium"
    return "low"


def _best_quant(opts: list[dict], user_vram: float | None) -> str:
    """Seleciona a melhor variante suportada pelo hardware."""
    effective = max(user_vram or 0, T4_VRAM)
    for opt in opts:  # ordenado full → q8 → q4 (maior para menor requisito)
        if effective >= opt["vram_gb"] * 1.2:
            return opt["type"]
    return opts[-1]["type"]  # q4_k_m como fallback


async def get_recommendations(hardware: dict) -> list[dict]:
    ram_gb  = hardware.get("ram_gb", 8)
    vram_gb = hardware.get("vram_gb")

    candidates = []
    for m in CANDIDATE_MODELS:
        min_vram = m["quant_options"][-1]["vram_gb"]  # Q4 = menor requisito
        compat   = _compat(min_vram, vram_gb)
        best_q   = _best_quant(m["quant_options"], vram_gb)
        opts_with_compat = [
            {**opt, "compatibility": _compat(opt["vram_gb"], vram_gb)}
            for opt in m["quant_options"]
        ]
        candidates.append({
            **m,
            "quant_options":  opts_with_compat,
            "compatibility":  compat,
            "selected_quant": best_q,
        })

    try:
        client     = get_openai_client()
        hw_summary = (
            f"RAM: {ram_gb}GB, GPU do usuario: {hardware.get('gpu', 'Nenhuma')}, "
            f"VRAM usuario: {vram_gb}GB, T4 Colab: 15GB VRAM disponivel"
        )
        prompt = (
            f"Hardware: {hw_summary}\n"
            f"Modelos: {json.dumps([c['name'] for c in candidates])}\n\n"
            "Retorne JSON com 'recommendations': lista dos 3-4 melhores modelos, cada um com: "
            "id, pros (2-3 itens), cons (1-2 itens), best_for (string curta)."
        )
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=700,
        )
        usage = response.usage
        if usage:
            record("gpt-4o-mini", "recommendation", usage.prompt_tokens, usage.completion_tokens)

        enriched = json.loads(response.choices[0].message.content or "{}")
        recs     = enriched.get("recommendations", [])
        result   = []
        for rec in recs:
            base = next((c for c in candidates if c["id"] == rec.get("id")), None)
            if base:
                result.append({**base, **rec})
        return result if result else candidates[:4]

    except Exception:
        return [c for c in candidates if c["compatibility"] != "low"][:4]
