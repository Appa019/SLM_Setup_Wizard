import json
from pathlib import Path

COLAB_DIR = Path(__file__).parent.parent.parent / "colab"
DATA_PROCESSED = Path(__file__).parent.parent.parent / "data" / "processed"


def generate_notebook(model_id: str, topic_profile: dict) -> Path:
    """Generate a Colab notebook for LoRA/QLoRA fine-tuning."""
    COLAB_DIR.mkdir(parents=True, exist_ok=True)

    model_map = {
        "llama-3.2-1b": "meta-llama/Llama-3.2-1B-Instruct",
        "llama-3.2-3b": "meta-llama/Llama-3.2-3B-Instruct",
        "phi-3-mini":   "microsoft/Phi-3-mini-4k-instruct",
        "mistral-7b":   "mistralai/Mistral-7B-Instruct-v0.3",
        "qwen2-7b":     "Qwen/Qwen2-7B-Instruct",
    }
    hf_model = model_map.get(model_id, "meta-llama/Llama-3.2-3B-Instruct")
    topic_area = topic_profile.get("area", "conhecimento geral")

    cells = [
        # Cell 0: Title
        _markdown_cell(f"# Fine-tuning: {topic_area}\n\nGerado automaticamente pelo Modelo SLM Local Wizard"),

        # Cell 1: Install deps
        _code_cell(
            "!pip install -q transformers peft bitsandbytes accelerate datasets trl sentencepiece\n"
            "!pip install -q llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121"
        ),

        # Cell 2: Imports
        _code_cell(
            "import json, os\n"
            "from pathlib import Path\n"
            "import torch\n"
            "from datasets import Dataset\n"
            "from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, BitsAndBytesConfig\n"
            "from peft import LoraConfig, get_peft_model\n"
            "from trl import SFTTrainer\n"
            'print(f"CUDA available: {torch.cuda.is_available()}")\n'
            'print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \'CPU\'}")'
        ),

        # Cell 3: Upload dataset
        _code_cell(
            "from google.colab import files\n"
            'print("Faca upload do arquivo training_data.jsonl")\n'
            "uploaded = files.upload()\n"
            "dataset_path = list(uploaded.keys())[0]\n"
            'print(f"Dataset carregado: {dataset_path}")'
        ),

        # Cell 4: Load dataset
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

        # Cell 5: Format dataset
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

        # Cell 6: Load model with QLoRA
        _code_cell(
            f'MODEL_ID = "{hf_model}"\n\n'
            "bnb_config = BitsAndBytesConfig(\n"
            "    load_in_4bit=True,\n"
            "    bnb_4bit_quant_type='nf4',\n"
            "    bnb_4bit_compute_dtype=torch.float16,\n"
            "    bnb_4bit_use_double_quant=True,\n"
            ")\n\n"
            "tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)\n"
            "tokenizer.pad_token = tokenizer.eos_token\n"
            "tokenizer.padding_side = 'right'\n\n"
            "model = AutoModelForCausalLM.from_pretrained(\n"
            "    MODEL_ID,\n"
            "    quantization_config=bnb_config,\n"
            "    device_map='auto',\n"
            "    trust_remote_code=True,\n"
            ")\n"
            'print("Modelo carregado!")'
        ),

        # Cell 7: LoRA config
        _code_cell(
            "lora_config = LoraConfig(\n"
            "    r=16,\n"
            "    lora_alpha=32,\n"
            "    target_modules=['q_proj', 'v_proj', 'k_proj', 'o_proj'],\n"
            "    lora_dropout=0.05,\n"
            "    bias='none',\n"
            "    task_type='CAUSAL_LM',\n"
            ")\n\n"
            "model = get_peft_model(model, lora_config)\n"
            "model.print_trainable_parameters()"
        ),

        # Cell 8: Training
        _code_cell(
            "training_args = TrainingArguments(\n"
            "    output_dir='./results',\n"
            "    num_train_epochs=3,\n"
            "    per_device_train_batch_size=2,\n"
            "    gradient_accumulation_steps=4,\n"
            "    learning_rate=2e-4,\n"
            "    fp16=True,\n"
            "    logging_steps=10,\n"
            "    save_steps=100,\n"
            "    warmup_ratio=0.03,\n"
            "    lr_scheduler_type='cosine',\n"
            "    report_to='none',\n"
            ")\n\n"
            "trainer = SFTTrainer(\n"
            "    model=model,\n"
            "    train_dataset=dataset['train'],\n"
            "    eval_dataset=dataset['test'],\n"
            "    dataset_text_field='text',\n"
            "    max_seq_length=2048,\n"
            "    tokenizer=tokenizer,\n"
            "    args=training_args,\n"
            "    peft_config=lora_config,\n"
            ")\n\n"
            "print('Iniciando treinamento...')\n"
            "trainer.train()\n"
            "print('Treinamento concluido!')"
        ),

        # Cell 9: Save merged model
        _code_cell(
            "from peft import PeftModel\n"
            "model.save_pretrained('./lora_adapter')\n"
            "tokenizer.save_pretrained('./lora_adapter')\n\n"
            "# Merge LoRA weights\n"
            "base_model = AutoModelForCausalLM.from_pretrained(\n"
            "    MODEL_ID, torch_dtype=torch.float16, device_map='auto', trust_remote_code=True\n"
            ")\n"
            "merged = PeftModel.from_pretrained(base_model, './lora_adapter')\n"
            "merged = merged.merge_and_unload()\n"
            "merged.save_pretrained('./merged_model')\n"
            "tokenizer.save_pretrained('./merged_model')\n"
            'print("Modelo merged salvo!")'
        ),

        # Cell 10: Convert to GGUF
        _code_cell(
            "!git clone https://github.com/ggerganov/llama.cpp /content/llama.cpp\n"
            "!pip install -q gguf\n"
            "!python /content/llama.cpp/convert_hf_to_gguf.py ./merged_model "
            "--outfile ./modelo_final.gguf --outtype q4_k_m\n"
            'print("Conversao para GGUF concluida!")\n'
            "import os\n"
            "size = os.path.getsize('./modelo_final.gguf') / (1024**3)\n"
            'print(f"Tamanho: {size:.2f} GB")'
        ),

        # Cell 11: Download
        _code_cell(
            "from google.colab import files\n"
            'print("Iniciando download do modelo GGUF...")\n'
            "files.download('./modelo_final.gguf')\n"
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

    output_path = COLAB_DIR / "generated_notebook.ipynb"
    output_path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2))
    return output_path


def _code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source,
    }


def _markdown_cell(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source,
    }
