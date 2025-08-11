import os
from datetime import datetime
from typing import List, Optional, Any

import uvicorn
from bson import ObjectId
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from minio import Minio
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, field_validator
from pydantic_core import core_schema

# --- Configuración de la Aplicación FastAPI ---
app = FastAPI(title="Google Drive Clone API", description="API para gestionar archivos, simulando la funcionalidad de Google Drive.", version="1.0.0")

# --- Configuración de CORS ---
origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Configuración de la Base de Datos (MongoDB) ---
DATABASE_URL = os.getenv("DATABASE_URL", "mongodb://mongodb:27017")
client = AsyncIOMotorClient(DATABASE_URL)
db = client.file_management
file_collection = db.get_collection("files")
folder_collection = db.get_collection("folders")

# --- Configuración de Almacenamiento (MinIO) ---
MINIO_URL = os.getenv("MINIO_URL", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
BUCKET_NAME = os.getenv("BUCKET_NAME", "files")

minio_client = Minio(MINIO_URL, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=False)


# --- Tipos Personalizados para Pydantic v2 ---
# Esta es la nueva forma de manejar ObjectId para que sea compatible con Pydantic v2
class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> core_schema.CoreSchema:
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(ObjectId),
                    core_schema.chain_schema(
                        [
                            core_schema.str_schema(),
                            core_schema.no_info_plain_validator_function(cls.validate),
                        ]
                    ),
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(lambda x: str(x)),
        )

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return cls(v)


# --- Modelos Pydantic (Serialización y Validación de Datos) ---
class FolderMetadata(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str = Field(..., min_length=1, max_length=100)
    parent_folder_id: Optional[PyObjectId] = None
    created_date: datetime = Field(default_factory=datetime.utcnow)
    path: str = "/"

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class FileMetadata(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    filename: str
    size: int
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    file_type: str
    object_name: str
    folder_id: Optional[PyObjectId] = None
    path: str = "/"

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class CreateFolder(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Nombre de la carpeta")
    parent_folder_id: Optional[str] = Field(None, description="ID de la carpeta padre (opcional)")


class UpdateFileName(BaseModel):
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


class MoveFile(BaseModel):
    folder_id: Optional[str] = Field(None, description="ID de la carpeta destino (null para raíz)")


class MoveFolder(BaseModel):
    parent_folder_id: Optional[str] = Field(None, description="ID de la carpeta padre destino (null para raíz)")


class CopyFile(BaseModel):
    folder_id: Optional[str] = Field(None, description="ID de la carpeta destino (null para raíz)")


class CopyFolder(BaseModel):
    parent_folder_id: Optional[str] = Field(None, description="ID de la carpeta padre destino (null para raíz)")


# --- Funciones de Ayuda ---
def create_bucket_if_not_exists():
    found = minio_client.bucket_exists(BUCKET_NAME)
    if not found:
        minio_client.make_bucket(BUCKET_NAME)
        print(f"Bucket '{BUCKET_NAME}' creado.")
    else:
        print(f"Bucket '{BUCKET_NAME}' ya existe.")


# --- Eventos de Inicio de la Aplicación ---
@app.on_event("startup")
async def startup_event():
    create_bucket_if_not_exists()


# --- Endpoints de la API ---


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {"message": "Google Drive Clone API is running", "status": "healthy", "version": "1.0.0"}


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check"""
    try:
        # Check database connection
        await file_collection.find_one()
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    try:
        # Check MinIO connection
        minio_client.bucket_exists(BUCKET_NAME)
        storage_status = "connected"
    except Exception:
        storage_status = "disconnected"

    return {
        "status": "healthy" if db_status == "connected" and storage_status == "connected" else "unhealthy",
        "database": db_status,
        "storage": storage_status,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/files/upload", response_model=FileMetadata, status_code=201)
async def upload_file(file: UploadFile = File(...), folder_id: Optional[str] = Form(None)):
    """
    Sube un archivo al sistema de almacenamiento.

    - **file**: Archivo a subir (cualquier tipo MIME)
    - **folder_id**: ID de la carpeta donde subir el archivo (opcional)
    - Retorna: Metadatos del archivo subido
    """
    # Validaciones
    if not file.filename:
        raise HTTPException(status_code=400, detail="El archivo debe tener un nombre")

    # Validar que la carpeta existe si se proporciona
    folder_path = "/"
    if folder_id:
        if not ObjectId.is_valid(folder_id):
            raise HTTPException(status_code=400, detail="ID de carpeta inválido")

        folder = await folder_collection.find_one({"_id": ObjectId(folder_id)})
        if not folder:
            raise HTTPException(status_code=404, detail="Carpeta no encontrada")
        folder_path = folder["path"]

    # Límite de tamaño (50MB)
    MAX_SIZE = 50 * 1024 * 1024
    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="El archivo es demasiado grande (máximo 50MB)")

    try:
        object_name = f"{ObjectId()}-{file.filename}"

        # Reset file pointer para MinIO
        await file.seek(0)

        minio_client.put_object(BUCKET_NAME, object_name, data=file.file, length=len(contents), content_type=file.content_type or "application/octet-stream")

        file_metadata = {
            "filename": file.filename,
            "size": len(contents),
            "upload_date": datetime.utcnow(),
            "file_type": file.content_type or "application/octet-stream",
            "object_name": object_name,
            "folder_id": ObjectId(folder_id) if folder_id else None,
            "path": folder_path,
        }

        result = await file_collection.insert_one(file_metadata)
        created_file = await file_collection.find_one({"_id": result.inserted_id})

        return created_file
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al subir el archivo: {str(e)}")


@app.get("/files", response_model=List[FileMetadata])
async def list_files(folder_id: Optional[str] = None, search: Optional[str] = None):
    """
    Lista archivos con filtros opcionales.

    - **folder_id**: Filtrar por carpeta específica
    - **search**: Buscar por nombre de archivo
    """
    query = {}

    # Filtrar por carpeta
    if folder_id:
        if folder_id == "root":
            query["folder_id"] = None
        else:
            if not ObjectId.is_valid(folder_id):
                raise HTTPException(status_code=400, detail="ID de carpeta inválido")
            query["folder_id"] = ObjectId(folder_id)

    # Filtrar por búsqueda
    if search:
        query["filename"] = {"$regex": search, "$options": "i"}

    files = await file_collection.find(query).to_list(1000)
    return files


@app.get("/files/download/{file_id}")
async def download_file(file_id: str, inline: Optional[bool] = False):
    """
    Descarga un archivo o lo muestra inline para preview.

    - **file_id**: ID del archivo
    - **inline**: Si es True, permite mostrar el archivo en el navegador (para preview)
    """
    if not ObjectId.is_valid(file_id):
        raise HTTPException(status_code=400, detail="ID de archivo inválido")

    file_metadata = await file_collection.find_one({"_id": ObjectId(file_id)})

    if not file_metadata:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    try:
        response = minio_client.get_object(BUCKET_NAME, file_metadata["object_name"])

        from fastapi.responses import StreamingResponse

        # Configurar headers según el tipo de archivo y parámetro inline
        headers = {}

        if inline and file_metadata["file_type"] in ["application/pdf", "image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"]:
            # Para preview: permitir mostrar inline
            headers["Content-Disposition"] = f"inline; filename={file_metadata['filename']}"
        else:
            # Para descarga: forzar attachment
            headers["Content-Disposition"] = f"attachment; filename={file_metadata['filename']}"

        return StreamingResponse(response.stream(32 * 1024), media_type=file_metadata["file_type"], headers=headers)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al descargar el archivo: {str(e)}")


@app.put("/files/edit/{file_id}", response_model=FileMetadata)
async def edit_file_name(file_id: str, file_update: UpdateFileName):
    if not ObjectId.is_valid(file_id):
        raise HTTPException(status_code=400, detail="ID de archivo inválido")

    update_result = await file_collection.update_one({"_id": ObjectId(file_id)}, {"$set": {"filename": file_update.new_filename}})

    if update_result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    updated_file = await file_collection.find_one({"_id": ObjectId(file_id)})
    return updated_file


@app.delete("/files/delete/{file_id}", status_code=204)
async def delete_file(file_id: str):
    if not ObjectId.is_valid(file_id):
        raise HTTPException(status_code=400, detail="ID de archivo inválido")

    file_metadata = await file_collection.find_one({"_id": ObjectId(file_id)})

    if not file_metadata:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    try:
        minio_client.remove_object(BUCKET_NAME, file_metadata["object_name"])
        await file_collection.delete_one({"_id": ObjectId(file_id)})
        return
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar el archivo: {str(e)}")


# --- Endpoints para Carpetas ---


@app.post("/folders", response_model=FolderMetadata, status_code=201)
async def create_folder(folder: CreateFolder):
    """
    Crea una nueva carpeta.

    - **name**: Nombre de la carpeta
    - **parent_folder_id**: ID de la carpeta padre (opcional)
    """
    # Validar que no exista una carpeta con el mismo nombre en el mismo directorio
    query = {"name": folder.name}
    if folder.parent_folder_id:
        if not ObjectId.is_valid(folder.parent_folder_id):
            raise HTTPException(status_code=400, detail="ID de carpeta padre inválido")
        query["parent_folder_id"] = ObjectId(folder.parent_folder_id)
    else:
        query["parent_folder_id"] = None

    existing_folder = await folder_collection.find_one(query)
    if existing_folder:
        raise HTTPException(status_code=400, detail="Ya existe una carpeta con ese nombre en este directorio")

    # Obtener ruta de la carpeta padre
    parent_path = "/"
    if folder.parent_folder_id:
        parent_folder = await folder_collection.find_one({"_id": ObjectId(folder.parent_folder_id)})
        if not parent_folder:
            raise HTTPException(status_code=404, detail="Carpeta padre no encontrada")
        parent_path = parent_folder["path"]

    # Construir ruta completa
    new_path = f"{parent_path.rstrip('/')}/{folder.name}/"

    folder_metadata = {
        "name": folder.name,
        "parent_folder_id": ObjectId(folder.parent_folder_id) if folder.parent_folder_id else None,
        "created_date": datetime.utcnow(),
        "path": new_path,
    }

    result = await folder_collection.insert_one(folder_metadata)
    created_folder = await folder_collection.find_one({"_id": result.inserted_id})
    return created_folder


@app.get("/folders", response_model=List[FolderMetadata])
async def list_folders(parent_folder_id: Optional[str] = None):
    """
    Lista carpetas en un directorio específico.

    - **parent_folder_id**: ID de la carpeta padre (None para root)
    """
    query = {}
    if parent_folder_id:
        if parent_folder_id == "root":
            query["parent_folder_id"] = None
        else:
            if not ObjectId.is_valid(parent_folder_id):
                raise HTTPException(status_code=400, detail="ID de carpeta inválido")
            query["parent_folder_id"] = ObjectId(parent_folder_id)
    else:
        query["parent_folder_id"] = None

    folders = await folder_collection.find(query).to_list(1000)
    return folders


@app.get("/folders/{folder_id}", response_model=FolderMetadata)
async def get_folder(folder_id: str):
    """Obtiene información de una carpeta específica"""
    if not ObjectId.is_valid(folder_id):
        raise HTTPException(status_code=400, detail="ID de carpeta inválido")

    folder = await folder_collection.find_one({"_id": ObjectId(folder_id)})
    if not folder:
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")

    return folder


@app.delete("/folders/{folder_id}", status_code=204)
async def delete_folder(folder_id: str):
    """
    Elimina una carpeta y todo su contenido.
    """
    if not ObjectId.is_valid(folder_id):
        raise HTTPException(status_code=400, detail="ID de carpeta inválido")

    folder = await folder_collection.find_one({"_id": ObjectId(folder_id)})
    if not folder:
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")

    try:
        # Eliminar archivos en la carpeta
        files_in_folder = await file_collection.find({"folder_id": ObjectId(folder_id)}).to_list(1000)
        for file_doc in files_in_folder:
            minio_client.remove_object(BUCKET_NAME, file_doc["object_name"])
            await file_collection.delete_one({"_id": file_doc["_id"]})

        # Eliminar subcarpetas recursivamente
        subfolders = await folder_collection.find({"parent_folder_id": ObjectId(folder_id)}).to_list(1000)
        for subfolder in subfolders:
            await delete_folder(str(subfolder["_id"]))

        # Eliminar la carpeta
        await folder_collection.delete_one({"_id": ObjectId(folder_id)})
        return

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar la carpeta: {str(e)}")


@app.get("/folders/{folder_id}/content")
async def get_folder_content(folder_id: str):
    """
    Obtiene el contenido completo de una carpeta (subcarpetas y archivos).
    """
    if folder_id != "root" and not ObjectId.is_valid(folder_id):
        raise HTTPException(status_code=400, detail="ID de carpeta inválido")

    # Obtener carpetas
    folder_query = {"parent_folder_id": None if folder_id == "root" else ObjectId(folder_id)}
    folders = await folder_collection.find(folder_query).to_list(1000)

    # Obtener archivos
    file_query = {"folder_id": None if folder_id == "root" else ObjectId(folder_id)}
    files = await file_collection.find(file_query).to_list(1000)

    # Convertir ObjectId a string para serialización JSON
    for folder in folders:
        folder["_id"] = str(folder["_id"])
        if folder.get("parent_folder_id"):
            folder["parent_folder_id"] = str(folder["parent_folder_id"])

    for file in files:
        file["_id"] = str(file["_id"])
        if file.get("folder_id"):
            file["folder_id"] = str(file["folder_id"])

    return {"folders": folders, "files": files, "folder_id": folder_id, "total_items": len(folders) + len(files)}


# --- Endpoints para Mover Elementos ---


@app.patch("/files/{file_id}/move", response_model=FileMetadata)
async def move_file(file_id: str, move_data: MoveFile):
    """
    Mueve un archivo a una carpeta diferente.

    - **file_id**: ID del archivo a mover
    - **folder_id**: ID de la carpeta destino (null para mover a raíz)
    """
    if not ObjectId.is_valid(file_id):
        raise HTTPException(status_code=400, detail="ID de archivo inválido")

    # Verificar que el archivo existe
    file_metadata = await file_collection.find_one({"_id": ObjectId(file_id)})
    if not file_metadata:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    # Validar carpeta destino si se proporciona
    target_folder_id = None
    target_path = "/"

    if move_data.folder_id:
        if not ObjectId.is_valid(move_data.folder_id):
            raise HTTPException(status_code=400, detail="ID de carpeta destino inválido")

        target_folder = await folder_collection.find_one({"_id": ObjectId(move_data.folder_id)})
        if not target_folder:
            raise HTTPException(status_code=404, detail="Carpeta destino no encontrada")

        target_folder_id = ObjectId(move_data.folder_id)
        target_path = target_folder["path"]

    try:
        # Actualizar archivo
        update_result = await file_collection.update_one({"_id": ObjectId(file_id)}, {"$set": {"folder_id": target_folder_id, "path": target_path}})

        if update_result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")

        # Devolver archivo actualizado
        updated_file = await file_collection.find_one({"_id": ObjectId(file_id)})
        return updated_file

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al mover archivo: {str(e)}")


@app.patch("/folders/{folder_id}/move", response_model=FolderMetadata)
async def move_folder(folder_id: str, move_data: MoveFolder):
    """
    Mueve una carpeta a una ubicación diferente.

    - **folder_id**: ID de la carpeta a mover
    - **parent_folder_id**: ID de la carpeta padre destino (null para mover a raíz)
    """
    if not ObjectId.is_valid(folder_id):
        raise HTTPException(status_code=400, detail="ID de carpeta inválido")

    # Verificar que la carpeta existe
    folder = await folder_collection.find_one({"_id": ObjectId(folder_id)})
    if not folder:
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")

    # Validar carpeta padre destino si se proporciona
    target_parent_id = None
    target_path = f"/{folder['name']}/"

    if move_data.parent_folder_id:
        if not ObjectId.is_valid(move_data.parent_folder_id):
            raise HTTPException(status_code=400, detail="ID de carpeta padre destino inválido")

        target_parent = await folder_collection.find_one({"_id": ObjectId(move_data.parent_folder_id)})
        if not target_parent:
            raise HTTPException(status_code=404, detail="Carpeta padre destino no encontrada")

        # Verificar que no se esté moviendo a sí misma o a una subcarpeta
        if move_data.parent_folder_id == folder_id:
            raise HTTPException(status_code=400, detail="No se puede mover una carpeta a sí misma")

        target_parent_id = ObjectId(move_data.parent_folder_id)
        target_path = f"{target_parent['path'].rstrip('/')}/{folder['name']}/"

    # Verificar que no existe una carpeta con el mismo nombre en el destino
    existing_folder = await folder_collection.find_one({"name": folder["name"], "parent_folder_id": target_parent_id, "_id": {"$ne": ObjectId(folder_id)}})
    if existing_folder:
        raise HTTPException(status_code=400, detail="Ya existe una carpeta con ese nombre en el destino")

    try:
        # Actualizar carpeta
        update_result = await folder_collection.update_one({"_id": ObjectId(folder_id)}, {"$set": {"parent_folder_id": target_parent_id, "path": target_path}})

        if update_result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Carpeta no encontrada")

        # TODO: Actualizar rutas de subcarpetas y archivos recursivamente
        # Por simplicidad, por ahora solo actualizamos la carpeta principal

        # Devolver carpeta actualizada
        updated_folder = await folder_collection.find_one({"_id": ObjectId(folder_id)})
        return updated_folder

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al mover carpeta: {str(e)}")


# --- Endpoints para Copiar Elementos ---


@app.post("/files/{file_id}/copy", response_model=FileMetadata, status_code=201)
async def copy_file(file_id: str, copy_data: CopyFile):
    """
    Copia un archivo a una carpeta diferente.

    - **file_id**: ID del archivo a copiar
    - **folder_id**: ID de la carpeta destino (null para copiar a raíz)
    """
    if not ObjectId.is_valid(file_id):
        raise HTTPException(status_code=400, detail="ID de archivo inválido")

    # Verificar que el archivo existe
    file_metadata = await file_collection.find_one({"_id": ObjectId(file_id)})
    if not file_metadata:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    # Validar carpeta destino si se proporciona
    target_folder_id = None
    target_path = "/"

    if copy_data.folder_id:
        if not ObjectId.is_valid(copy_data.folder_id):
            raise HTTPException(status_code=400, detail="ID de carpeta destino inválido")

        target_folder = await folder_collection.find_one({"_id": ObjectId(copy_data.folder_id)})
        if not target_folder:
            raise HTTPException(status_code=404, detail="Carpeta destino no encontrada")

        target_folder_id = ObjectId(copy_data.folder_id)
        target_path = target_folder["path"]

    try:
        # Obtener el archivo original de MinIO
        original_response = minio_client.get_object(BUCKET_NAME, file_metadata["object_name"])
        file_data = original_response.read()
        original_response.close()

        # Crear nuevo object_name para la copia
        new_object_name = f"{ObjectId()}-{file_metadata['filename']}"

        # Subir la copia a MinIO
        from io import BytesIO

        file_stream = BytesIO(file_data)
        minio_client.put_object(BUCKET_NAME, new_object_name, data=file_stream, length=len(file_data), content_type=file_metadata["file_type"])

        # Crear metadatos para el archivo copiado
        copied_file_metadata = {
            "filename": file_metadata["filename"],
            "size": file_metadata["size"],
            "upload_date": datetime.utcnow(),
            "file_type": file_metadata["file_type"],
            "object_name": new_object_name,
            "folder_id": target_folder_id,
            "path": target_path,
        }

        # Insertar el archivo copiado en la base de datos
        result = await file_collection.insert_one(copied_file_metadata)
        copied_file = await file_collection.find_one({"_id": result.inserted_id})

        return copied_file

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al copiar archivo: {str(e)}")


@app.post("/folders/{folder_id}/copy", response_model=FolderMetadata, status_code=201)
async def copy_folder(folder_id: str, copy_data: CopyFolder):
    """
    Copia una carpeta a una ubicación diferente.

    - **folder_id**: ID de la carpeta a copiar
    - **parent_folder_id**: ID de la carpeta padre destino (null para copiar a raíz)
    """
    if not ObjectId.is_valid(folder_id):
        raise HTTPException(status_code=400, detail="ID de carpeta inválido")

    # Verificar que la carpeta existe
    folder = await folder_collection.find_one({"_id": ObjectId(folder_id)})
    if not folder:
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")

    # Validar carpeta padre destino si se proporciona
    target_parent_id = None
    target_path = f"/{folder['name']}/"

    if copy_data.parent_folder_id:
        if not ObjectId.is_valid(copy_data.parent_folder_id):
            raise HTTPException(status_code=400, detail="ID de carpeta padre destino inválido")

        target_parent = await folder_collection.find_one({"_id": ObjectId(copy_data.parent_folder_id)})
        if not target_parent:
            raise HTTPException(status_code=404, detail="Carpeta padre destino no encontrada")

        target_parent_id = ObjectId(copy_data.parent_folder_id)
        target_path = f"{target_parent['path'].rstrip('/')}/{folder['name']}/"

    # Verificar que no existe una carpeta con el mismo nombre en el destino
    existing_folder = await folder_collection.find_one({"name": folder["name"], "parent_folder_id": target_parent_id})
    if existing_folder:
        # Si existe, agregar un sufijo para diferenciar
        base_name = folder["name"]
        counter = 1
        while existing_folder:
            new_name = f"{base_name} - Copia ({counter})"
            existing_folder = await folder_collection.find_one({"name": new_name, "parent_folder_id": target_parent_id})
            if not existing_folder:
                folder["name"] = new_name
                target_path = f"{target_parent['path'].rstrip('/')}/{new_name}/" if copy_data.parent_folder_id else f"/{new_name}/"
                break
            counter += 1

    try:
        # Crear la nueva carpeta
        copied_folder_metadata = {
            "name": folder["name"],
            "parent_folder_id": target_parent_id,
            "created_date": datetime.utcnow(),
            "path": target_path,
        }

        result = await folder_collection.insert_one(copied_folder_metadata)
        copied_folder = await folder_collection.find_one({"_id": result.inserted_id})

        # TODO: Copiar recursivamente subcarpetas y archivos
        # Por simplicidad, por ahora solo copiamos la carpeta principal

        return copied_folder

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al copiar carpeta: {str(e)}")


# --- Punto de Entrada para Ejecutar la Aplicación ---
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
