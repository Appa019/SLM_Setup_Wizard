import base64
import json
import re
import uuid
from datetime import datetime
from pathlib import Path

COLAB_DIR      = Path(__file__).parent.parent.parent / "colab"
MODELS_DIR     = Path(__file__).parent.parent.parent / "models"
DATA_PROCESSED = Path(__file__).parent.parent.parent / "data" / "processed"

MODEL_MAP = {
    "llama-3.2-1b": "meta-llama/Llama-3.2-1B-Instruct",
    "llama-3.2-3b": "meta-llama/Llama-3.2-3B-Instruct",
    "phi-3-mini":   "microsoft/Phi-3-mini-4k-instruct",
    "mistral-7b":   "mistralai/Mistral-7B-Instruct-v0.3",
    "qwen2-7b":     "Qwen/Qwen2-7B-Instruct",
}


def make_slug(topic_area: str, model_id: str) -> str:
    """Deriva slug unico: {topic}_{model_id}_{YYYYMMDD-HHMMSS}."""
    topic_slug = re.sub(r"[^a-z0-9]+", "-", topic_area.lower()).strip("-")[:30]
    ts         = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{topic_slug}_{model_id}_{ts}"


def write_sidecar(slug: str, topic_profile: dict, model_id: str,
                  quant_type: str, training_target: str) -> None:
    """Grava models/{slug}.json com metadata do especialista."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    meta = {
        "slug":            slug,
        "topic":           topic_profile.get("area", "Conhecimento Geral"),
        "subtopics":       topic_profile.get("subtopics", []),
        "base_model":      model_id,
        "quant_type":      quant_type,
        "training_target": training_target,
        "created_at":      datetime.now().isoformat(timespec="seconds"),
    }
    (MODELS_DIR / f"{slug}.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _build_dataset_cell(dataset_path: Path | None) -> dict:
    """Gera célula que escreve o dataset diretamente em /content/training_data.jsonl.

    Se dataset_path existir, embute os dados em base64 — sem interação do usuário.
    Caso contrário, gera célula de fallback que pede upload manual.
    """
    target = "/content/training_data.jsonl"

    if dataset_path and dataset_path.exists():
        raw_bytes = dataset_path.read_bytes()
        b64 = base64.b64encode(raw_bytes).decode("ascii")
        # Quebrar em linhas de 76 chars para legibilidade no notebook
        chunks = [b64[i:i+76] for i in range(0, len(b64), 76)]
        lines_repr = '(\n    "' + '"\n    "'.join(chunks) + '"\n)'
        source = (
            "import base64\n"
            f"_DATA_B64 = {lines_repr}\n"
            f"with open('{target}', 'wb') as _f:\n"
            "    _f.write(base64.b64decode(_DATA_B64))\n"
            f'dataset_path = "{target}"\n'
            f'print(f"Dataset pronto: {{dataset_path}} ({{len(open(dataset_path).readlines())}} linhas)")'
        )
    else:
        # Fallback: upload manual (comportamento antigo)
        source = (
            "from google.colab import files\n"
            'print("Dataset nao embutido — faca upload do training_data.jsonl")\n'
            "uploaded = files.upload()\n"
            "dataset_path = list(uploaded.keys())[0]\n"
            'print(f"Dataset carregado: {dataset_path}")'
        )

    return _code_cell(source)


def generate_notebook(model_id: str, topic_profile: dict,
                      params: dict | None = None,
                      model_slug: str = "especialista",
                      hf_id: str = "",
                      dataset_path: Path | None = None) -> Path:
    """Gera notebook Colab com celula de configuracao dinamica da IA."""
    COLAB_DIR.mkdir(parents=True, exist_ok=True)
    hf_model   = hf_id if hf_id else MODEL_MAP.get(model_id, "meta-llama/Llama-3.2-3B-Instruct")
    topic_area = topic_profile.get("area", "conhecimento geral")
    p          = params or {}
    gguf_name  = f"{model_slug}.gguf"

    config_cell = _code_cell(
        "# ╔══════════════════════════════════════════╗\n"
        "# ║  CONFIGURACAO GERADA PELA IA (GPT-5.1)  ║\n"
        "# ║  Ajuste manualmente se necessario        ║\n"
        "# ╚══════════════════════════════════════════╝\n"
        f'MODEL_ID                  = "{hf_model}"\n'
        f'TRAINING_TARGET           = "{p.get("training_target", "colab")}"\n'
        f'QUANTIZATION              = "{p.get("quantization", "4bit")}"\n'
        f'USE_CPU_OFFLOAD           = {p.get("use_cpu_offload", False)}\n'
        f'LORA_R                    = {p.get("lora_r", 16)}\n'
        f'LORA_ALPHA                = {p.get("lora_alpha", 32)}\n'
        f'TARGET_MODULES            = {json.dumps(p.get("target_modules", ["q_proj", "v_proj", "k_proj", "o_proj"]))}\n'
        f'LORA_DROPOUT              = {p.get("lora_dropout", 0.05)}\n'
        f'MAX_SEQ_LENGTH            = {p.get("max_seq_length", 1024)}\n'
        f'BATCH_SIZE                = {p.get("batch_size", 2)}\n'
        f'GRADIENT_ACCUMULATION     = {p.get("gradient_accumulation_steps", 8)}\n'
        f'NUM_EPOCHS                = {p.get("num_epochs", 3)}\n'
        f'LEARNING_RATE             = {p.get("learning_rate", 2e-4)}\n'
        f'WARMUP_RATIO              = {p.get("warmup_ratio", 0.03)}\n'
        f'WEIGHT_DECAY              = {p.get("weight_decay", 0.01)}\n'
        f'USE_FLASH_ATTENTION       = {p.get("use_flash_attention", False)}\n'
        f'GRADIENT_CHECKPOINTING    = {p.get("gradient_checkpointing", True)}\n'
        f'FP16                      = {p.get("fp16", True)}\n'
        f'BF16                      = {p.get("bf16", False)}\n'
        f'GGUF_QUANT_TYPE           = "{p.get("gguf_quantization_type", "q4_k_m")}"\n'
        f'# Justificativa IA: {p.get("justification", "Parametros padrao")}\n'
        f'# Decisao de treino: {p.get("training_target_reason", "")}'
    )

    cells = [
        # Cell 0: Title
        _markdown_cell(f"# Fine-tuning: {topic_area}\n\nGerado automaticamente pelo Modelo SLM Local Wizard"),

        # Cell 1: Config gerada pela IA (PRIMEIRO — editavel pelo usuario)
        config_cell,

        # Cell 2: Install deps
        _code_cell(
            "!pip install -q transformers peft bitsandbytes accelerate datasets trl sentencepiece\n"
            "!pip install -q llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121"
        ),

        # Cell 3: Imports
        _code_cell(
            "import json, os\n"
            "from pathlib import Path\n"
            "import torch\n"
            "from datasets import Dataset\n"
            "from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig\n"
            "from peft import LoraConfig\n"
            "from trl import SFTTrainer, SFTConfig\n"
            'print(f"CUDA available: {torch.cuda.is_available()}")\n'
            'print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \'CPU\'}")'
        ),

        # Cell 4: Dataset embutido em base64 (sem interação do usuário)
        _build_dataset_cell(dataset_path),

        # Cell 5: Load dataset
        _code_cell(
            "def load_jsonl(path):\n"
            "    data = []\n"
            "    with open(path, 'r', encoding='utf-8') as f:\n"
            "        for line in f:\n"
            "            line = line.strip()\n"
            "            if line:\n"
            "                data.append(json.loads(line))\n"
            "    return data\n\n"
            "raw_data = load_jsonl(dataset_path)\n"
            "print(f'Total de pares: {len(raw_data)}')\n"
            "print('Exemplo:', raw_data[0] if raw_data else 'vazio')"
        ),

        # Cell 6: Format dataset
        _code_cell(
            "def format_instruction(sample):\n"
            "    instruction = sample.get('instruction', '')\n"
            "    inp = sample.get('input', '')\n"
            "    output = sample.get('output', '')\n"
            "    if inp:\n"
            "        return f'### Instrucao:\\n{instruction}\\n\\n### Contexto:\\n{inp}\\n\\n### Resposta:\\n{output}'\n"
            "    return f'### Instrucao:\\n{instruction}\\n\\n### Resposta:\\n{output}'\n\n"
            "formatted = [{'text': format_instruction(d)} for d in raw_data]\n"
            "dataset = Dataset.from_list(formatted)\n"
            "dataset = dataset.train_test_split(test_size=0.1)\n"
            "print(dataset)"
        ),

        # Cell 7: Load model with dynamic quantization
        _code_cell(
            "# Carrega modelo com quantizacao definida pela IA\n"
            "if QUANTIZATION == '4bit':\n"
            "    bnb_config = BitsAndBytesConfig(\n"
            "        load_in_4bit=True,\n"
            "        bnb_4bit_quant_type='nf4',\n"
            "        bnb_4bit_compute_dtype=torch.bfloat16 if BF16 else torch.float16,\n"
            "        bnb_4bit_use_double_quant=True,\n"
            "    )\n"
            "    model_kwargs = {'quantization_config': bnb_config, 'device_map': 'auto', 'trust_remote_code': True}\n"
            "elif QUANTIZATION == '8bit':\n"
            "    model_kwargs = {'load_in_8bit': True, 'device_map': 'auto', 'trust_remote_code': True}\n"
            "else:\n"
            "    dtype = torch.bfloat16 if BF16 else torch.float16\n"
            "    model_kwargs = {'torch_dtype': dtype, 'device_map': 'auto', 'trust_remote_code': True}\n\n"
            "tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)\n"
            "tokenizer.pad_token = tokenizer.eos_token\n"
            "tokenizer.padding_side = 'right'\n\n"
            "model = AutoModelForCausalLM.from_pretrained(MODEL_ID, **model_kwargs)\n"
            'print("Modelo carregado!")'
        ),

        # Cell 8: LoRA config + Training (SFTConfig API)
        _code_cell(
            "lora_config = LoraConfig(\n"
            "    r=LORA_R,\n"
            "    lora_alpha=LORA_ALPHA,\n"
            "    target_modules=TARGET_MODULES,\n"
            "    lora_dropout=LORA_DROPOUT,\n"
            "    bias='none',\n"
            "    task_type='CAUSAL_LM',\n"
            ")\n\n"
            "training_args = SFTConfig(\n"
            "    output_dir='./results',\n"
            "    num_train_epochs=NUM_EPOCHS,\n"
            "    per_device_train_batch_size=BATCH_SIZE,\n"
            "    gradient_accumulation_steps=GRADIENT_ACCUMULATION,\n"
            "    learning_rate=LEARNING_RATE,\n"
            "    fp16=FP16,\n"
            "    bf16=BF16,\n"
            "    gradient_checkpointing=GRADIENT_CHECKPOINTING,\n"
            "    logging_steps=10,\n"
            "    save_steps=100,\n"
            "    warmup_ratio=WARMUP_RATIO,\n"
            "    weight_decay=WEIGHT_DECAY,\n"
            "    lr_scheduler_type='cosine',\n"
            "    report_to='none',\n"
            "    max_length=MAX_SEQ_LENGTH,\n"
            ")\n\n"
            "trainer = SFTTrainer(\n"
            "    model=model,\n"
            "    train_dataset=dataset['train'],\n"
            "    eval_dataset=dataset['test'],\n"
            "    processing_class=tokenizer,\n"
            "    args=training_args,\n"
            "    peft_config=lora_config,\n"
            ")\n\n"
            "trainer.model.print_trainable_parameters()\n"
            "print('Iniciando treinamento...')\n"
            "trainer.train()\n"
            "print('Treinamento concluido!')"
        ),

        # Cell 9: Save merged model
        _code_cell(
            "from peft import PeftModel\n"
            "trainer.model.save_pretrained('./lora_adapter')\n"
            "tokenizer.save_pretrained('./lora_adapter')\n\n"
            "base_model = AutoModelForCausalLM.from_pretrained(\n"
            "    MODEL_ID, torch_dtype=torch.float16, device_map='auto', trust_remote_code=True\n"
            ")\n"
            "merged = PeftModel.from_pretrained(base_model, './lora_adapter')\n"
            "merged = merged.merge_and_unload()\n"
            "merged.save_pretrained('./merged_model')\n"
            "tokenizer.save_pretrained('./merged_model')\n"
            'print("Modelo merged salvo!")'
        ),

        # Cell 10: Convert to GGUF (two-step: f16 + quantize)
        _code_cell(
            "!git clone https://github.com/ggerganov/llama.cpp /content/llama.cpp\n"
            "!pip install -q gguf\n"
            "!cd /content/llama.cpp && cmake -B build && cmake --build build --config Release -j\n\n"
            "!python /content/llama.cpp/convert_hf_to_gguf.py ./merged_model "
            "--outfile ./model-f16.gguf --outtype f16\n\n"
            "import subprocess, shutil\n"
            "DIRECT_TYPES = {'f16', 'f32', 'bf16', 'q8_0'}\n"
            "if GGUF_QUANT_TYPE.lower() in DIRECT_TYPES:\n"
            f"    shutil.move('./model-f16.gguf', './{gguf_name}')\n"
            "    print(f'Modelo salvo como {{GGUF_QUANT_TYPE}} (direto)')\n"
            "else:\n"
            "    subprocess.run([\n"
            "        '/content/llama.cpp/build/bin/llama-quantize',\n"
            f"        './model-f16.gguf', './{gguf_name}', GGUF_QUANT_TYPE\n"
            "    ], check=True)\n"
            "    import os as _os\n"
            "    _os.remove('./model-f16.gguf')\n"
            "    print(f'Quantizado para {{GGUF_QUANT_TYPE}}')\n\n"
            "import os\n"
            f"size = os.path.getsize('./{gguf_name}') / (1024**3)\n"
            'print(f"Tamanho: {size:.2f} GB")'
        ),

        # Cell 11: Download
        _code_cell(
            "from google.colab import files\n"
            'print("Iniciando download do modelo GGUF...")\n'
            f"files.download('./{gguf_name}')\n"
            'print("Download iniciado!")'
        ),
    ]

    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10.0"},
            "accelerator": "GPU",
            "colab": {"provenance": []},
        },
        "cells": cells,
    }

    output_path = COLAB_DIR / f"{model_slug}.ipynb"
    output_path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2))
    return output_path


def generate_local_script(model_id: str, topic_profile: dict,
                           params: dict | None = None,
                           model_slug: str = "especialista",
                           hf_id: str = "") -> Path:
    """Gera script Python puro para treinamento local (GPU usuario > T4)."""
    COLAB_DIR.mkdir(parents=True, exist_ok=True)
    hf_model   = hf_id if hf_id else MODEL_MAP.get(model_id, "meta-llama/Llama-3.2-3B-Instruct")
    topic_area = topic_profile.get("area", "conhecimento geral")
    p          = params or {}
    gguf_name = f"{model_slug}.gguf"

    script = (
        "#!/usr/bin/env python3\n"
        f'"""Fine-tuning local: {topic_area} — Gerado pelo Modelo SLM Local Wizard"""\n\n'
        "# ╔══════════════════════════════════════════╗\n"
        "# ║  CONFIGURACAO GERADA PELA IA (GPT-5.1)  ║\n"
        "# ║  Ajuste manualmente se necessario        ║\n"
        "# ╚══════════════════════════════════════════╝\n"
        f'MODEL_ID                  = "{hf_model}"\n'
        f'TRAINING_TARGET           = "local"\n'
        f'QUANTIZATION              = "{p.get("quantization", "4bit")}"\n'
        f'USE_CPU_OFFLOAD           = {p.get("use_cpu_offload", False)}\n'
        f'LORA_R                    = {p.get("lora_r", 16)}\n'
        f'LORA_ALPHA                = {p.get("lora_alpha", 32)}\n'
        f'TARGET_MODULES            = {json.dumps(p.get("target_modules", ["q_proj", "v_proj", "k_proj", "o_proj"]))}\n'
        f'LORA_DROPOUT              = {p.get("lora_dropout", 0.05)}\n'
        f'MAX_SEQ_LENGTH            = {p.get("max_seq_length", 2048)}\n'
        f'BATCH_SIZE                = {p.get("batch_size", 4)}\n'
        f'GRADIENT_ACCUMULATION     = {p.get("gradient_accumulation_steps", 4)}\n'
        f'NUM_EPOCHS                = {p.get("num_epochs", 3)}\n'
        f'LEARNING_RATE             = {p.get("learning_rate", 2e-4)}\n'
        f'WARMUP_RATIO              = {p.get("warmup_ratio", 0.03)}\n'
        f'WEIGHT_DECAY              = {p.get("weight_decay", 0.01)}\n'
        f'USE_FLASH_ATTENTION       = {p.get("use_flash_attention", False)}\n'
        f'GRADIENT_CHECKPOINTING    = {p.get("gradient_checkpointing", True)}\n'
        f'FP16                      = {p.get("fp16", True)}\n'
        f'BF16                      = {p.get("bf16", False)}\n'
        f'GGUF_QUANT_TYPE           = "{p.get("gguf_quantization_type", "q8_0")}"\n'
        f'DATASET_PATH              = "../data/processed/training_data.jsonl"\n'
        f'OUTPUT_DIR                = "./results"\n'
        f'# Justificativa IA: {p.get("justification", "Parametros padrao")}\n'
        f'# Decisao de treino: {p.get("training_target_reason", "GPU local superior ao T4")}\n\n'
        "import json, os\n"
        "import torch\n"
        "from datasets import Dataset\n"
        "from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig\n"
        "from peft import LoraConfig, PeftModel\n"
        "from trl import SFTTrainer, SFTConfig\n\n"
        "print(f'CUDA: {torch.cuda.is_available()}')\n"
        "print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU\"}')\n\n"
        "# Carregar dataset\n"
        "def load_jsonl(path):\n"
        "    data = []\n"
        "    with open(path, 'r', encoding='utf-8') as f:\n"
        "        for line in f:\n"
        "            line = line.strip()\n"
        "            if line:\n"
        "                data.append(json.loads(line))\n"
        "    return data\n\n"
        "raw_data = load_jsonl(DATASET_PATH)\n"
        "print(f'Pares de treinamento: {len(raw_data)}')\n\n"
        "def format_instruction(sample):\n"
        "    instruction = sample.get('instruction', '')\n"
        "    inp = sample.get('input', '')\n"
        "    output = sample.get('output', '')\n"
        "    if inp:\n"
        "        return f'### Instrucao:\\n{instruction}\\n\\n### Contexto:\\n{inp}\\n\\n### Resposta:\\n{output}'\n"
        "    return f'### Instrucao:\\n{instruction}\\n\\n### Resposta:\\n{output}'\n\n"
        "formatted = [{'text': format_instruction(d)} for d in raw_data]\n"
        "dataset = Dataset.from_list(formatted).train_test_split(test_size=0.1)\n\n"
        "# Carregar modelo\n"
        "if QUANTIZATION == '4bit':\n"
        "    bnb_config = BitsAndBytesConfig(\n"
        "        load_in_4bit=True, bnb_4bit_quant_type='nf4',\n"
        "        bnb_4bit_compute_dtype=torch.bfloat16 if BF16 else torch.float16,\n"
        "        bnb_4bit_use_double_quant=True,\n"
        "    )\n"
        "    model_kwargs = {'quantization_config': bnb_config, 'device_map': 'auto', 'trust_remote_code': True}\n"
        "elif QUANTIZATION == '8bit':\n"
        "    model_kwargs = {'load_in_8bit': True, 'device_map': 'auto', 'trust_remote_code': True}\n"
        "else:\n"
        "    dtype = torch.bfloat16 if BF16 else torch.float16\n"
        "    model_kwargs = {'torch_dtype': dtype, 'device_map': 'auto', 'trust_remote_code': True}\n\n"
        "tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)\n"
        "tokenizer.pad_token = tokenizer.eos_token\n"
        "tokenizer.padding_side = 'right'\n"
        "model = AutoModelForCausalLM.from_pretrained(MODEL_ID, **model_kwargs)\n\n"
        "lora_config = LoraConfig(\n"
        "    r=LORA_R, lora_alpha=LORA_ALPHA, target_modules=TARGET_MODULES,\n"
        "    lora_dropout=LORA_DROPOUT, bias='none', task_type='CAUSAL_LM',\n"
        ")\n\n"
        "training_args = SFTConfig(\n"
        "    output_dir=OUTPUT_DIR, num_train_epochs=NUM_EPOCHS,\n"
        "    per_device_train_batch_size=BATCH_SIZE,\n"
        "    gradient_accumulation_steps=GRADIENT_ACCUMULATION,\n"
        "    learning_rate=LEARNING_RATE, fp16=FP16, bf16=BF16,\n"
        "    gradient_checkpointing=GRADIENT_CHECKPOINTING,\n"
        "    logging_steps=10, save_steps=100, warmup_ratio=WARMUP_RATIO,\n"
        "    weight_decay=WEIGHT_DECAY, lr_scheduler_type='cosine', report_to='none',\n"
        "    max_length=MAX_SEQ_LENGTH,\n"
        ")\n\n"
        "trainer = SFTTrainer(\n"
        "    model=model, train_dataset=dataset['train'], eval_dataset=dataset['test'],\n"
        "    processing_class=tokenizer, args=training_args, peft_config=lora_config,\n"
        ")\n"
        "trainer.model.print_trainable_parameters()\n"
        "print('Iniciando treinamento local...')\n"
        "trainer.train()\n"
        "print('Treinamento concluido!')\n\n"
        "# Salvar adapter e fazer merge\n"
        "trainer.model.save_pretrained('./lora_adapter')\n"
        "tokenizer.save_pretrained('./lora_adapter')\n"
        "print('Adapter salvo em ./lora_adapter')\n\n"
        "base_model = AutoModelForCausalLM.from_pretrained(\n"
        "    MODEL_ID, torch_dtype=torch.float16, device_map='auto', trust_remote_code=True\n"
        ")\n"
        "merged = PeftModel.from_pretrained(base_model, './lora_adapter')\n"
        "merged = merged.merge_and_unload()\n"
        "merged.save_pretrained('./merged_model')\n"
        "tokenizer.save_pretrained('./merged_model')\n"
        "print('Modelo merged salvo em ./merged_model')\n\n"
        "# Converter para GGUF (dois passos)\n"
        "import subprocess, shutil\n"
        "print('Convertendo para GGUF...')\n"
        "subprocess.run(['python', 'llama.cpp/convert_hf_to_gguf.py', './merged_model',\n"
        "    '--outfile', './model-f16.gguf', '--outtype', 'f16'], check=True)\n"
        "DIRECT_TYPES = {'f16', 'f32', 'bf16', 'q8_0'}\n"
        "if GGUF_QUANT_TYPE.lower() in DIRECT_TYPES:\n"
        f"    shutil.move('./model-f16.gguf', './{gguf_name}')\n"
        "    print(f'Modelo salvo como {{GGUF_QUANT_TYPE}} (direto)')\n"
        "else:\n"
        "    subprocess.run(['llama.cpp/build/bin/llama-quantize',\n"
        f"        './model-f16.gguf', './{gguf_name}', GGUF_QUANT_TYPE], check=True)\n"
        "    os.remove('./model-f16.gguf')\n"
        "    print(f'Quantizado para {{GGUF_QUANT_TYPE}}')\n"
        f"size = os.path.getsize('./{gguf_name}') / (1024**3)\n"
        "print(f'Tamanho final: {{size:.2f}} GB')\n"
    )

    output_path = COLAB_DIR / f"{model_slug}_local.py"
    output_path.write_text(script, encoding="utf-8")

    # Gerar requirements.txt
    req_path = COLAB_DIR / "requirements.txt"
    req_path.write_text(
        "torch>=2.5.0\n"
        "transformers>=4.47.0\n"
        "peft>=0.14.0\n"
        "bitsandbytes>=0.45.0\n"
        "accelerate>=1.2.0\n"
        "datasets>=3.2.0\n"
        "trl>=0.29.0\n"
        "sentencepiece\n"
        "gguf\n"
    )
    return output_path


def _split_source(source: str) -> list[str]:
    """Converte source string em lista de linhas (padrao nbformat 4.5+)."""
    lines = source.split("\n")
    return [line + "\n" for line in lines[:-1]] + ([lines[-1]] if lines[-1] else [])


def _code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": uuid.uuid4().hex[:8],
        "metadata": {},
        "outputs": [],
        "source": _split_source(source),
    }


def _markdown_cell(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "id": uuid.uuid4().hex[:8],
        "metadata": {},
        "source": _split_source(source),
    }
