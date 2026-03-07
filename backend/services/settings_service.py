import os
from openai import AsyncOpenAI
from utils.storage import write_env, read_env


def save_openai_key(api_key: str):
    write_env({"OPENAI_API_KEY": api_key})
    os.environ["OPENAI_API_KEY"] = api_key


async def validate_openai_key(api_key: str) -> bool:
    try:
        client = AsyncOpenAI(api_key=api_key)
        await client.models.list()
        return True
    except Exception:
        return False


def get_status() -> dict:
    env = read_env()
    key = env.get("OPENAI_API_KEY", "")
    email = env.get("GOOGLE_EMAIL", "")
    return {
        "openai_configured": bool(key and key.startswith("sk-")),
        "google_email": email,
    }
