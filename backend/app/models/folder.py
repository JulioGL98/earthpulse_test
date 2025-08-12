from datetime import datetime
from typing import Optional
from pydantic import Field
from app.models.base import BaseDocument, PyObjectId


class FolderMetadata(BaseDocument):
    """Modelo para metadatos de carpetas"""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str = Field(..., min_length=1, max_length=100)
    parent_folder_id: Optional[PyObjectId] = None
    created_date: datetime = Field(default_factory=datetime.utcnow)
    path: str = "/"
    owner: Optional[str] = None


class CreateFolder(BaseDocument):
    """Esquema para crear carpeta"""

    name: str = Field(..., min_length=1, max_length=100, description="Nombre de la carpeta")
    parent_folder_id: Optional[str] = Field(None, description="ID de la carpeta padre (opcional)")


class MoveFolder(BaseDocument):
    """Esquema para mover carpeta"""

    parent_folder_id: Optional[str] = Field(None, description="ID de la carpeta padre destino (null para raíz)")


class CopyFolder(BaseDocument):
    """Esquema para copiar carpeta"""

    parent_folder_id: Optional[str] = Field(None, description="ID de la carpeta padre destino (null para raíz)")
