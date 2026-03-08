"""Recomenda modelos open-source para fine-tuning usando GPT-5.1 (Responses API).
GPT-5.1 escolhe dinamicamente os melhores modelos do ecossistema HuggingFace.
"""
import json
from openai import AsyncOpenAI
from config import settings
from services.cost_tracker import record

SYSTEM_PROMPT = (
    "You are an expert ML engineer specializing in LLM fine-tuning and the HuggingFace open-source "
    "model ecosystem. You have deep knowledge of all fine-tunable language models available on "
    "HuggingFace as of 2025-2026, including LLaMA 3.x, Phi-3/4, Mistral, Qwen2, Gemma 2, "
    "SmolLM, Falcon, DeepSeek, and others.\n\n"
    "Your task: Given hardware specs, recommend the BEST 3-4 open-source LLMs for LoRA/QLoRA "
    "fine-tuning. Criteria:\n"
    "1. HARDWARE FIT: Model must run in QLoRA (4-bit) on available VRAM. Use Colab T4 (15GB) as "
    "baseline if user VRAM is lower.\n"
    "2. FINE-TUNING SUPPORT: Only models compatible with HuggingFace PEFT + SFTTrainer.\n"
    "3. QUALITY: Prefer highest quality for the hardware. Consider instruction-following, "
    "Portuguese/multilingual support, reasoning.\n"
    "4. VARIETY: Different families when possible.\n\n"
    "VRAM rules (approximations):\n"
    "  Full FP16 training: params_B * 2.0 GB\n"
    "  Q8_0 QLoRA:         params_B * 1.0 GB\n"
    "  Q4_K_M QLoRA:       params_B * 0.5 GB\n\n"
    "Return ONLY a valid JSON object — no markdown, no code fences:\n"
    "{\n"
    '  "recommendations": [\n'
    "    {\n"
    '      "id": "short-slug-lowercase-hyphenated",\n'
    '      "name": "Human readable name",\n'
    '      "params": "3B",\n'
    '      "family": "LLaMA 3",\n'
    '      "hf_id": "exact/huggingface-model-id",\n'
    '      "description": "2-3 sentence description of strengths and use cases in Portuguese.",\n'
    '      "context_window": 131072,\n'
    '      "license": "Apache 2.0",\n'
    '      "quant_options": [\n'
    '        {"type": "full",   "label": "Full (FP16)",    "vram_gb": 6.5},\n'
    '        {"type": "q8",     "label": "Q8_0 (8-bit)",   "vram_gb": 3.5},\n'
    '        {"type": "q4_k_m", "label": "Q4_K_M (4-bit)", "vram_gb": 2.0}\n'
    "      ],\n"
    '      "pros": ["pro 1 in Portuguese", "pro 2", "pro 3"],\n'
    '      "cons": ["con 1 in Portuguese", "con 2"],\n'
    '      "best_for": "short use case description in Portuguese"\n'
    "    }\n"
    "  ]\n"
    "}"
)

_EFFECTIVE_T4 = 15.0


def _compat(vram_needed: float, effective: float) -> str:
    if effective >= vram_needed * 1.4:
        return "high"
    if effective >= vram_needed:
        return "medium"
    return "low"


def _best_quant(opts: list[dict], effective: float) -> str:
    for opt in opts:
        if effective >= opt["vram_gb"] * 1.2:
            return opt["type"]
    return opts[-1]["type"]


def _enrich(recs: list[dict], effective: float) -> list[dict]:
    """Adiciona compatibility e selected_quant a cada modelo e variante."""
    for m in recs:
        opts = m.get("quant_options", [])
        if opts:
            min_vram = min(o["vram_gb"] for o in opts)
            m["compatibility"]  = _compat(min_vram, effective)
            m["selected_quant"] = _best_quant(opts, effective)
            m["quant_options"]  = [
                {**o, "compatibility": _compat(o["vram_gb"], effective)}
                for o in opts
            ]
    return recs


FALLBACK_MODELS: list[dict] = [
    {
        "id": "llama-3.2-1b", "name": "LLaMA 3.2 1B", "params": "1B",
        "family": "LLaMA 3", "hf_id": "meta-llama/Llama-3.2-1B-Instruct",
        "description": "Modelo ultra-leve da Meta. Surpreendentemente capaz para seu tamanho, com context window gigante de 128k tokens.",
        "context_window": 131072, "license": "Meta Community License",
        "quant_options": [
            {"type": "full",   "label": "Full (FP16)",    "vram_gb": 2.5},
            {"type": "q8",     "label": "Q8_0 (8-bit)",   "vram_gb": 1.3},
            {"type": "q4_k_m", "label": "Q4_K_M (4-bit)", "vram_gb": 0.8},
        ],
        "pros": ["Ultra leve, roda em qualquer hardware", "Context window 128k", "Fine-tuning muito rapido"],
        "cons": ["Capacidade de raciocinio limitada vs modelos maiores"],
        "best_for": "Hardware limitado, inferencia rapida",
    },
    {
        "id": "llama-3.2-3b", "name": "LLaMA 3.2 3B", "params": "3B",
        "family": "LLaMA 3", "hf_id": "meta-llama/Llama-3.2-3B-Instruct",
        "description": "Excelente equilibrio entre tamanho e qualidade. Boa escolha geral para fine-tuning especializado, com suporte a 128k tokens.",
        "context_window": 131072, "license": "Meta Community License",
        "quant_options": [
            {"type": "full",   "label": "Full (FP16)",    "vram_gb": 6.5},
            {"type": "q8",     "label": "Q8_0 (8-bit)",   "vram_gb": 3.5},
            {"type": "q4_k_m", "label": "Q4_K_M (4-bit)", "vram_gb": 2.0},
        ],
        "pros": ["Otimo custo-beneficio", "Context window 128k", "Fine-tuning eficiente no Colab T4"],
        "cons": ["Menos capaz que modelos 7B+"],
        "best_for": "Fine-tuning geral, melhor escolha para Colab",
    },
    {
        "id": "phi-3-mini", "name": "Phi-3 Mini 3.8B", "params": "3.8B",
        "family": "Phi-3", "hf_id": "microsoft/Phi-3-mini-4k-instruct",
        "description": "Modelo da Microsoft treinado com dados sinteticos de alta qualidade. Raciocinio excepcional para seu tamanho.",
        "context_window": 4096, "license": "MIT",
        "quant_options": [
            {"type": "full",   "label": "Full (FP16)",    "vram_gb": 7.5},
            {"type": "q8",     "label": "Q8_0 (8-bit)",   "vram_gb": 4.0},
            {"type": "q4_k_m", "label": "Q4_K_M (4-bit)", "vram_gb": 2.4},
        ],
        "pros": ["Raciocinio excepcional", "Licenca MIT (uso comercial livre)", "Eficiente em tarefas analiticas"],
        "cons": ["Context window curto (4k)", "Menos multilingual"],
        "best_for": "Tarefas analiticas e raciocinio, licenca comercial",
    },
    {
        "id": "mistral-7b", "name": "Mistral 7B v0.3", "params": "7B",
        "family": "Mistral", "hf_id": "mistralai/Mistral-7B-Instruct-v0.3",
        "description": "Referencia em qualidade para modelos 7B. Excelente seguimento de instrucoes e raciocinio. Licenca Apache 2.0.",
        "context_window": 32768, "license": "Apache 2.0",
        "quant_options": [
            {"type": "full",   "label": "Full (FP16)",    "vram_gb": 14.5},
            {"type": "q8",     "label": "Q8_0 (8-bit)",   "vram_gb": 8.0},
            {"type": "q4_k_m", "label": "Q4_K_M (4-bit)", "vram_gb": 4.5},
        ],
        "pros": ["Melhor qualidade 7B", "Apache 2.0 (comercial)", "Excelente em instrucao e raciocinio"],
        "cons": ["Mais pesado para fine-tuning no Colab T4"],
        "best_for": "Maxima qualidade com hardware adequado",
    },
]


async def get_recommendations(hardware: dict) -> list[dict]:
    ram_gb    = hardware.get("ram_gb", 8)
    vram_gb   = hardware.get("vram_gb")
    gpu       = hardware.get("gpu") or "Nenhuma GPU detectada"
    effective = max(vram_gb or 0, _EFFECTIVE_T4)

    user_message = (
        f"User hardware:\n"
        f"- GPU: {gpu}\n"
        f"- User VRAM: {vram_gb or 0} GB\n"
        f"- Effective VRAM for training (max of user VRAM and Colab T4): {effective} GB\n"
        f"- RAM: {ram_gb} GB\n\n"
        f"Recommend the best 3-4 open-source LLMs for LoRA/QLoRA fine-tuning on this hardware. "
        f"Prefer models with good Portuguese language support. Return JSON only."
    )

    try:
        client   = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.responses.create(
            model="gpt-5.1",
            reasoning={"effort": "high"},
            store=True,
            tools=[{"type": "web_search_preview"}],
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
        )

        usage = getattr(response, "usage", None)
        if usage:
            record(
                "gpt-5.1", "model_recommendation",
                getattr(usage, "input_tokens", 0),
                getattr(usage, "output_tokens", 0),
            )

        output_text = ""
        for item in response.output:
            if getattr(item, "type", "") == "message":
                for block in item.content:
                    if getattr(block, "type", "") == "output_text":
                        output_text = block.text
                        break

        start = output_text.find("{")
        end   = output_text.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(output_text[start:end])
            recs = data.get("recommendations", [])
            if recs:
                return _enrich(recs, effective)

    except Exception:
        pass

    return _enrich(list(FALLBACK_MODELS), effective)
