"""
Gera hiperparametros otimos para fine-tuning usando GPT-5.1 via Responses API.
Decide tambem se treinar localmente (GPU usuario > T4) ou no Colab T4.
"""
import json
from openai import AsyncOpenAI
from config import settings
from services.cost_tracker import record

T4_VRAM_GB = 15.0  # VRAM do Colab T4 free tier

MONSTROUS_PROMPT = (
    "You are Dr. Alex Chen, a world-class ML systems engineer and computational "
    "neuroscientist with 15+ years of experience in LLM fine-tuning, GPU memory optimization, and "
    "production deployment of transformer models. You have co-authored papers on QLoRA, contributed "
    "to the bitsandbytes library, and optimized training runs on hardware ranging from a Raspberry Pi "
    "to a 512-GPU H100 cluster.\n\n"
    "Your task: given hardware specs and a base model, compute the EXACT optimal training configuration "
    "that maximizes model quality while fitting within hardware constraints — with ZERO tolerance for "
    "OOM errors. You must DO THE MATH explicitly before deciding each parameter.\n\n"
    "PHYSICS YOU MUST APPLY:\n\n"
    "1. VRAM BUDGET (bytes):\n"
    "   full_weights    = params × dtype_bytes  (fp32=4, fp16=2, int8=1, int4=0.5)\n"
    "   gradients       = full_weights (same dtype as compute)\n"
    "   optimizer_states = full_weights × 8    (Adam: m + v in fp32)\n"
    "   activations     = batch × seq_len × hidden × layers × 2  (fp16)\n"
    "   KV_cache        = 2 × layers × heads × head_dim × seq_len × batch × dtype_bytes\n"
    "   QLoRA budget    = base_4bit + lora_weights_fp16 + activations + KV_cache\n"
    "   lora_params     = 2 × r × (d_model × n_target_modules)\n\n"
    "2. QUANTIZATION SELECTION RULES:\n"
    "   effective_vram >= full_weights × 1.4  → quantization = none  (fp16 full)\n"
    "   effective_vram >= full_weights × 0.7  → quantization = 8bit  (bitsandbytes LLM.int8)\n"
    "   effective_vram >= full_weights × 0.35 → quantization = 4bit  (QLoRA NF4)\n"
    "   effective_vram <  full_weights × 0.35 → quantization = 4bit + CPU offload (device_map=auto)\n"
    "   No GPU at all                         → training_feasible = false (use llama.cpp only)\n\n"
    "3. TRAINING TARGET DECISION:\n"
    "   user_vram > T4_vram (15GB)  → training_target = \"local\"  (train on user GPU)\n"
    "   user_vram <= 15GB OR no GPU → training_target = \"colab\"  (use Colab T4)\n"
    "   Always state WHY you chose local vs colab.\n\n"
    "4. LORA RANK SELECTION:\n"
    "   dataset_pairs < 1000  → r = 8   (avoid overfitting)\n"
    "   dataset_pairs 1k-5k   → r = 16  (standard)\n"
    "   dataset_pairs > 5k    → r = 32  (rich representation)\n"
    "   r MUST be power of 2: 4, 8, 16, 32, 64\n"
    "   lora_alpha = 2 × r    (maintains gradient scale invariance)\n"
    "   TARGET MODULES by architecture:\n"
    "     LLaMA/Mistral: [\"q_proj\",\"k_proj\",\"v_proj\",\"o_proj\",\"gate_proj\",\"up_proj\",\"down_proj\"]\n"
    "     Phi-3:         [\"q_proj\",\"k_proj\",\"v_proj\",\"dense\"]\n"
    "     Qwen2:         [\"q_proj\",\"k_proj\",\"v_proj\",\"o_proj\",\"up_proj\",\"down_proj\"]\n\n"
    "5. BATCH SIZE + GRADIENT ACCUMULATION:\n"
    "   target_effective_batch = 16\n"
    "   T4 / 15GB VRAM:     batch_size = 1-2,  grad_accumulation = 8-16\n"
    "   A100-40GB:          batch_size = 4-8,  grad_accumulation = 2-4\n"
    "   RTX 3090/4090 24GB: batch_size = 2-4,  grad_accumulation = 4-8\n"
    "   V100 16GB:          batch_size = 2,    grad_accumulation = 8\n"
    "   CPU only:           batch_size = 1,    grad_accumulation = 16\n"
    "   Verify: batch_size × grad_accumulation = ~16\n\n"
    "6. SEQUENCE LENGTH:\n"
    "   Memory for activations: seq_len × batch × hidden × layers × 4 bytes < 0.25 × effective_vram_bytes\n"
    "   Colab T4:         max_seq_length = 1024  (2048 with gradient_checkpointing)\n"
    "   >20GB VRAM:       max_seq_length = 2048 or 4096\n\n"
    "7. EPOCHS & LEARNING RATE:\n"
    "   num_epochs = max(3, min(10, int(10000 / dataset_pairs)))\n"
    "   learning_rate = 2e-4 if lora_r <= 16 else 1e-4\n"
    "   warmup_ratio = 0.03\n"
    "   lr_scheduler_type = \"cosine\"  (always)\n"
    "   weight_decay = 0.01\n\n"
    "8. FLASH ATTENTION 2:\n"
    "   ONLY enable if GPU architecture is Ampere (A100, RTX 3000+) or newer\n"
    "   T4 = Turing → flash_attention = False  (NOT supported)\n"
    "   V100 = Volta → flash_attention = False\n"
    "   RTX 3090/4090 = Ampere/Ada → flash_attention = True\n\n"
    "9. GRADIENT CHECKPOINTING:\n"
    "   Enable when: effective_vram < model_full_size × 2\n"
    "   Reduces activation memory ~10x at 30% compute overhead\n"
    "   Almost always True for Colab T4\n\n"
    "10. GGUF QUANTIZATION FOR INFERENCE (after training):\n"
    "    user_vram < 4GB  → gguf_type = \"q4_k_m\"\n"
    "    user_vram < 8GB  → gguf_type = \"q5_k_m\"\n"
    "    user_vram >= 8GB → gguf_type = \"q8_0\"\n"
    "    CPU only         → gguf_type = \"q4_k_m\"\n\n"
    "HARDWARE REFERENCE:\n"
    "  T4:          15GB VRAM, Turing,   16GB RAM,  Colab free tier\n"
    "  V100:        16GB VRAM, Volta,    supports bf16\n"
    "  A100-40:     40GB VRAM, Ampere,   supports FA2, bf16\n"
    "  RTX 3090:    24GB VRAM, Ampere,   supports FA2\n"
    "  RTX 4090:    24GB VRAM, Ada,      supports FA2\n"
    "  RTX 3080:    10GB VRAM, Ampere\n"
    "  GTX 1080Ti:  11GB VRAM, Pascal,   NO FA2, NO bf16\n"
    "  CPU:         0 VRAM — training NOT recommended for models >1B\n\n"
    "IMPORTANT OUTPUT FORMAT:\n"
    "Return ONLY a valid JSON object with these exact fields:\n"
    "{\n"
    "  \"training_target\": \"colab\" | \"local\",\n"
    "  \"training_target_reason\": \"string explaining why\",\n"
    "  \"quantization\": \"none\" | \"8bit\" | \"4bit\",\n"
    "  \"use_cpu_offload\": true | false,\n"
    "  \"lora_r\": 8 | 16 | 32,\n"
    "  \"lora_alpha\": 16 | 32 | 64,\n"
    "  \"target_modules\": [\"list\", \"of\", \"modules\"],\n"
    "  \"lora_dropout\": 0.05,\n"
    "  \"max_seq_length\": 512 | 1024 | 2048 | 4096,\n"
    "  \"batch_size\": 1 | 2 | 4 | 8,\n"
    "  \"gradient_accumulation_steps\": 4 | 8 | 16,\n"
    "  \"num_epochs\": 3..10,\n"
    "  \"learning_rate\": 0.0001 | 0.0002,\n"
    "  \"warmup_ratio\": 0.03,\n"
    "  \"weight_decay\": 0.01,\n"
    "  \"use_flash_attention\": true | false,\n"
    "  \"gradient_checkpointing\": true | false,\n"
    "  \"gguf_quantization_type\": \"q4_k_m\" | \"q5_k_m\" | \"q8_0\",\n"
    "  \"fp16\": true | false,\n"
    "  \"bf16\": true | false,\n"
    "  \"training_feasible\": true | false,\n"
    "  \"justification\": \"2-3 sentences explaining key decisions with the math\"\n"
    "}"
)


async def generate_hyperparams(
    model_id:      str,
    quant_type:    str,
    hardware:      dict,
    dataset_pairs: int = 2000,
) -> dict:
    """
    Chama GPT-5.1 via Responses API com reasoning high para gerar
    hiperparametros otimos. Decide local vs Colab automaticamente.
    Se user_vram > T4 (15GB) → training_target = 'local', senao 'colab'.
    """
    client    = AsyncOpenAI(api_key=settings.openai_api_key)
    user_vram = hardware.get("vram_gb") or 0
    gpu_name  = hardware.get("gpu") or "Nenhuma GPU detectada"
    ram_gb    = hardware.get("ram_gb", 8)

    user_message = (
        f"Generate optimal fine-tuning hyperparameters for this exact scenario:\n\n"
        f"BASE MODEL: {model_id}\n"
        f"REQUESTED QUANTIZATION: {quant_type} (full=fp16, q8=8bit, q4_k_m=4bit NF4)\n"
        f"USER GPU: {gpu_name}\n"
        f"USER VRAM: {user_vram} GB\n"
        f"USER RAM: {ram_gb} GB\n"
        f"COLAB T4 VRAM: {T4_VRAM_GB} GB (always available as fallback)\n"
        f"ESTIMATED DATASET SIZE: {dataset_pairs} instruction-output pairs\n\n"
        f"Training target rule: if user_vram ({user_vram}GB) > T4 ({T4_VRAM_GB}GB) "
        f"→ training_target = local (train on user GPU). Otherwise → colab.\n"
        f"Do the math. Return the JSON."
    )

    try:
        response = await client.responses.create(
            model="gpt-5.1",
            reasoning={"effort": "high"},
            store=True,
            input=[
                {"role": "system", "content": MONSTROUS_PROMPT},
                {"role": "user",   "content": user_message},
            ],
        )

        # Extrair uso de tokens para custo
        usage = getattr(response, "usage", None)
        if usage:
            record(
                "gpt-5.1", "hyperparams",
                getattr(usage, "input_tokens", 0),
                getattr(usage, "output_tokens", 0),
            )

        # Extrair texto da resposta
        output_text = ""
        for item in response.output:
            if getattr(item, "type", "") == "message":
                for block in item.content:
                    if getattr(block, "type", "") == "output_text":
                        output_text = block.text
                        break

        # Parse JSON
        start = output_text.find("{")
        end   = output_text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(output_text[start:end])

    except Exception:
        pass

    # Fallback conservador
    return _conservative_defaults(model_id, user_vram, dataset_pairs)


def _conservative_defaults(model_id: str, user_vram: float, dataset_pairs: int) -> dict:
    """Defaults conservadores quando GPT-5.1 nao esta disponivel."""
    target = "local" if user_vram > T4_VRAM_GB else "colab"
    r      = 8 if dataset_pairs < 1000 else (16 if dataset_pairs < 5000 else 32)
    vram   = max(user_vram, T4_VRAM_GB)
    gguf   = "q4_k_m" if vram < 4 else ("q5_k_m" if vram < 8 else "q8_0")
    return {
        "training_target":              target,
        "training_target_reason":       (
            f"User VRAM ({user_vram}GB) {'>' if target == 'local' else '<='} T4 (15GB) — "
            f"treinando {'localmente' if target == 'local' else 'no Colab T4'}"
        ),
        "quantization":                 "4bit",
        "use_cpu_offload":              False,
        "lora_r":                       r,
        "lora_alpha":                   r * 2,
        "target_modules":               ["q_proj", "k_proj", "v_proj", "o_proj"],
        "lora_dropout":                 0.05,
        "max_seq_length":               1024,
        "batch_size":                   2,
        "gradient_accumulation_steps":  8,
        "num_epochs":                   3,
        "learning_rate":                2e-4,
        "warmup_ratio":                 0.03,
        "weight_decay":                 0.01,
        "use_flash_attention":          False,
        "gradient_checkpointing":       True,
        "gguf_quantization_type":       gguf,
        "fp16":                         True,
        "bf16":                         False,
        "training_feasible":            True,
        "justification":                f"Defaults conservadores para {target}. VRAM efetiva: {vram}GB.",
    }
