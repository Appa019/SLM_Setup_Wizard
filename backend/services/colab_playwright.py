import asyncio
from pathlib import Path

training_state: dict = {
    "running": False,
    "step": "",
    "steps_done": [],
    "log": [],
    "metrics": {"epoch": 0, "loss": None, "step": 0},
    "finished": False,
    "error": "",
    "model_path": "",
}

STEPS = [
    "Abrindo Google Colab...",
    "Verificando login...",
    "Fazendo upload do notebook...",
    "Configurando runtime GPU...",
    "Iniciando execucao das celulas...",
    "Instalando dependencias...",
    "Carregando dataset...",
    "Carregando modelo base...",
    "Treinando (LoRA/QLoRA)...",
    "Convertendo para GGUF...",
    "Baixando modelo...",
]


def get_training_state() -> dict:
    return dict(training_state)


def _log(msg: str):
    training_state["log"] = (training_state["log"] + [msg])[-50:]  # Keep last 50


async def run_colab_automation(notebook_path: Path, dataset_path: Path, model_out_dir: Path):
    """
    Abre o Google Colab no browser padrao do sistema e monitora a pasta models/
    aguardando o arquivo .gguf gerado pelo treinamento.
    """
    import webbrowser

    global training_state
    training_state.update({
        "running": True, "step": STEPS[0], "steps_done": [], "log": [],
        "metrics": {"epoch": 0, "loss": None, "step": 0},
        "finished": False, "error": "", "model_path": "",
    })

    try:
        # Passo 1: Abrir Colab no browser real do usuario
        _update_step(STEPS[0])
        colab_url = "https://colab.research.google.com"
        _log(f"Abrindo {colab_url} no browser padrao...")
        webbrowser.open(colab_url)
        await asyncio.sleep(3)

        # Passo 2: Instruções para o usuario
        _update_step("Aguardando acoes manuais no Colab...")
        _log("=" * 42)
        _log("ACOES NECESSARIAS NO BROWSER:")
        _log("1. Faca login na conta Google se solicitado")
        _log("2. File > Upload notebook")
        _log(f"   Arquivo: {notebook_path.name}")
        _log("3. Runtime > Change runtime type > T4 GPU")
        _log("4. Runtime > Run all  (Ctrl+F9)")
        _log("5. Na celula de upload: selecione training_data.jsonl")
        _log(f"6. Aguarde o fim e faca download do modelo_final.gguf")
        _log(f"   Salve em: {model_out_dir}/")
        _log("=" * 42)

        # Passo 3: Monitorar models/ aguardando .gguf
        _update_step("Monitorando pasta models/ aguardando modelo_final.gguf...")
        model_out_dir.mkdir(parents=True, exist_ok=True)

        for i in range(360):  # ate 60 minutos (360 x 10s)
            await asyncio.sleep(10)
            elapsed = (i + 1) * 10
            _log(f"Aguardando .gguf... {elapsed}s decorridos")
            training_state["metrics"]["step"] = elapsed

            gguf_files = list(model_out_dir.glob("*.gguf"))
            if gguf_files:
                model_path = str(gguf_files[0])
                _log(f"Modelo GGUF detectado: {gguf_files[0].name}")
                training_state["model_path"] = model_path
                _update_step("Modelo recebido com sucesso!")
                break
        else:
            _log("Timeout de 60 minutos atingido sem detectar .gguf.")
            _log("Se o modelo ja foi baixado, coloque o .gguf em models/ e reinicie o dashboard.")

    except Exception as e:
        training_state["error"] = str(e)
        _log(f"Erro: {e}")

    training_state["running"] = False
    training_state["finished"] = True
    _log("Automacao Colab finalizada")


def _update_step(step: str):
    training_state["step"] = step
    training_state["steps_done"].append(step)
    _log(step)
