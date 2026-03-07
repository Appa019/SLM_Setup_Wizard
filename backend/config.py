import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega .env no startup para persistir chaves entre reinicializacoes
load_dotenv(Path(__file__).parent / ".env", override=False)


class Settings:
    """Le variaveis sensiveis diretamente do os.environ (atualizado em runtime)."""

    @property
    def openai_api_key(self) -> str:
        return os.environ.get("OPENAI_API_KEY", "")

    @property
    def google_email(self) -> str:
        return os.environ.get("GOOGLE_EMAIL", "")

    data_dir:   Path = Path(__file__).parent / "data"
    models_dir: Path = Path(__file__).parent / "models"


settings = Settings()
