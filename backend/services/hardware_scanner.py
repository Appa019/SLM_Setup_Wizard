import platform
import psutil
import subprocess
import shutil


def _get_gpu_info() -> dict | None:
    # Try nvidia-smi first
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                text=True, timeout=5
            ).strip()
            if out:
                parts = out.split(",")
                name = parts[0].strip()
                vram_mb = int(parts[1].strip()) if len(parts) > 1 else 0
                return {"model": name, "vram_gb": round(vram_mb / 1024, 1)}
        except Exception:
            pass

    # Try GPUtil
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            g = gpus[0]
            return {"model": g.name, "vram_gb": round(g.memoryTotal / 1024, 1)}
    except Exception:
        pass

    return None


def _classify_capacity(ram_gb: float, vram_gb: float | None) -> dict:
    effective = vram_gb if vram_gb else ram_gb * 0.5
    if effective >= 16:
        return {"max_params": "13B+", "tier": "high", "label": "Alto desempenho"}
    elif effective >= 8:
        return {"max_params": "7B", "tier": "mid", "label": "Desempenho medio"}
    elif effective >= 4:
        return {"max_params": "3B", "tier": "low", "label": "Desempenho basico"}
    else:
        return {"max_params": "1B", "tier": "minimal", "label": "Capacidade minima"}


def scan() -> dict:
    cpu = platform.processor() or platform.machine()
    cpu_cores = psutil.cpu_count(logical=True)
    cpu_freq = psutil.cpu_freq()
    cpu_freq_ghz = round(cpu_freq.max / 1000, 2) if cpu_freq else 0

    ram = psutil.virtual_memory()
    ram_total_gb = round(ram.total / (1024 ** 3), 1)
    ram_available_gb = round(ram.available / (1024 ** 3), 1)

    disk = psutil.disk_usage("/")
    disk_free_gb = round(disk.free / (1024 ** 3), 1)

    gpu = _get_gpu_info()
    capacity = _classify_capacity(ram_total_gb, gpu["vram_gb"] if gpu else None)

    return {
        "cpu": {
            "model": cpu,
            "cores": cpu_cores,
            "freq_ghz": cpu_freq_ghz,
        },
        "ram": {
            "total_gb": ram_total_gb,
            "available_gb": ram_available_gb,
        },
        "gpu": gpu,
        "disk": {
            "free_gb": disk_free_gb,
        },
        "os": f"{platform.system()} {platform.release()}",
        "capacity": capacity,
    }
