import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega arquivo .env da raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Pizzaria Fellice - Controle de Estoque")
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", "fellice-super-secret-key-change-in-production-random-jwt-token"
    )
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./fellice.db")


settings = Settings()
