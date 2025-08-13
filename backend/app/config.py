import os
from typing import Optional


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mongodb://mongodb:27017")
    DATABASE_NAME: str = "file_management"

    MINIO_URL: str = os.getenv("MINIO_URL", "minio:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    BUCKET_NAME: str = os.getenv("BUCKET_NAME", "files")

    SECRET_KEY: str = os.getenv("SECRET_KEY", "change_me_dev_secret_key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    API_TITLE: str = "Google Drive Clone API"
    API_DESCRIPTION: str = "API para gestionar archivos, simulando la funcionalidad de Google Drive."
    API_VERSION: str = "1.0.0"

    ALLOWED_ORIGINS: list = [
        "http://localhost:5173",
    ]

    MAX_FILE_SIZE: int = 50 * 1024 * 1024


settings = Settings()
