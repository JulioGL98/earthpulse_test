from datetime import datetime
from typing import Optional
from pydantic import Field, field_validator
from app.models.base import BaseDocument, PyObjectId


class FileMetadata(BaseDocument):
    """Modelo para metadatos de archivos"""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    filename: str
    size: int
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    file_type: str
    object_name: str
    folder_id: Optional[PyObjectId] = None
    path: str = "/"
    owner: Optional[str] = None


class UpdateFileName(BaseDocument):
    """Esquema para actualizar nombre de archivo"""

    new_filename: str = Field(..., min_length=1, max_length=255, description="Nuevo nombre del archivo")

    @field_validator("new_filename")
    @classmethod
    def validate_filename(cls, v):
        if not v or not v.strip():
            raise ValueError("El nombre del archivo no puede estar vacío")

        # Caracteres no permitidos en nombres de archivo
        invalid_chars = '<>:"/\\|?*'
        if any(char in v for char in invalid_chars):
            raise ValueError(f"El nombre del archivo contiene caracteres no válidos: {invalid_chars}")

        return v.strip()


class MoveFile(BaseDocument):
    """Esquema para mover archivo"""

    folder_id: Optional[str] = Field(None, description="ID de la carpeta destino (null para raíz)")


class CopyFile(BaseDocument):
    """Esquema para copiar archivo"""

    folder_id: Optional[str] = Field(None, description="ID de la carpeta destino (null para raíz)")
