import asyncio
import json
import subprocess
import shutil
from pathlib import Path

MODELS_DIR = Path(__file__).parent.parent.parent / "models"

_server_proc: subprocess.Popen | None = None
_loaded_model: str = ""
_server_port: int = 8080


def find_gguf_models() -> list[dict]:
    """Lista todos os .gguf em models/, enriquecendo com sidecar .json se existir."""
    if not MODELS_DIR.exists():
        return []
    models = []
    for f in MODELS_DIR.glob("*.gguf"):
        size_gb  = round(f.stat().st_size / (1024 ** 3), 2)
        sidecar  = f.with_suffix(".json")
        meta: dict = {}
        if sidecar.exists():
            try:
                meta = json.loads(sidecar.read_text(encoding="utf-8"))
            except Exception:
                pass
        models.append({
            "name":            f.name,
            "path":            str(f),
            "size_gb":         size_gb,
            "topic":           meta.get("topic", f.stem),
            "base_model":      meta.get("base_model", ""),
            "quant_type":      meta.get("quant_type", ""),
            "training_target": meta.get("training_target", ""),
            "created_at":      meta.get("created_at", ""),
            "subtopics":       meta.get("subtopics", []),
        })
    return sorted(models, key=lambda m: m.get("created_at", m["name"]), reverse=True)


def is_llama_available() -> bool:
    return bool(shutil.which("llama-server") or shutil.which("llama-cli"))


def get_status() -> dict:
    global _server_proc, _loaded_model
    running = _server_proc is not None and _server_proc.poll() is None
    return {
        "llama_available": is_llama_available(),
        "models": find_gguf_models(),
        "server_running": running,
        "loaded_model": _loaded_model if running else "",
        "server_port": _server_port if running else None,
    }


async def load_model(model_name: str) -> dict:
    global _server_proc, _loaded_model

    model_path = MODELS_DIR / model_name
    if not model_path.exists():
        return {"ok": False, "error": f"Modelo nao encontrado: {model_name}"}

    if not is_llama_available():
        return {"ok": False, "error": "llama-server nao instalado. Instale o llama.cpp."}

    # Stop any existing server
    await stop_model()

    cmd = [
        "llama-server",
        "--model", str(model_path),
        "--port", str(_server_port),
        "--ctx-size", "2048",
        "--n-predict", "512",
        "--threads", "4",
        "--host", "127.0.0.1",
    ]

    try:
        _server_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _loaded_model = model_name
        # Give it a moment to start
        await asyncio.sleep(3)
        if _server_proc.poll() is not None:
            return {"ok": False, "error": "llama-server encerrou inesperadamente"}
        return {"ok": True, "port": _server_port, "model": model_name}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def stop_model():
    global _server_proc, _loaded_model
    if _server_proc and _server_proc.poll() is None:
        _server_proc.terminate()
        try:
            _server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _server_proc.kill()
    _server_proc = None
    _loaded_model = ""


async def chat_with_model(message: str, history: list[dict]) -> str:
    """Send a chat message to the running llama-server."""
    import httpx

    if not (_server_proc and _server_proc.poll() is None):
        return "Nenhum modelo carregado. Carregue um modelo primeiro."

    # Build messages array
    messages = history + [{"role": "user", "content": message}]

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"http://127.0.0.1:{_server_port}/v1/chat/completions",
                json={
                    "model": _loaded_model,
                    "messages": messages,
                    "max_tokens": 512,
                    "temperature": 0.7,
                },
                timeout=60,
            )
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Erro ao comunicar com llama-server: {e}"
