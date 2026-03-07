from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    openai_api_key: str = ""
    google_email: str = ""
    data_dir: Path = Path(__file__).parent / "data"
    models_dir: Path = Path(__file__).parent / "models"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
