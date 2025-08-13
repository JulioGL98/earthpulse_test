from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from fastapi import UploadFile
from minio.api import CopySource

from app.config import settings
from app.database import file_collection, folder_collection, minio_client
from app.models.file import CopyFile, FileMetadata, MoveFile, UpdateFileName
from app.services.auth_service import AuthService
from app.utils.exceptions import InternalServerException, NotFoundException, ValidationException
from app.utils.validators import validate_object_id


class FileService:
    @staticmethod
    def _check_ownership(resource: Optional[dict], current_user: dict, not_found_message: str = "Recurso no encontrado"):
        if not resource:
            raise NotFoundException(not_found_message)
        if AuthService.is_admin(current_user):
            return
        owner = resource.get("owner")
        if owner is None:
            raise NotFoundException(not_found_message)
        if owner != current_user.get("username"):
            raise NotFoundException(not_found_message)

    @staticmethod
    async def upload_file(file: UploadFile, current_user: dict, folder_id: Optional[str] = None) -> dict:
        if not file.filename:
            raise ValidationException("El archivo debe tener un nombre")

        folder_path = "/"
        if folder_id:
            folder_oid = validate_object_id(folder_id, "ID de carpeta")
            folder = await folder_collection.find_one({"_id": folder_oid})
            FileService._check_ownership(folder, current_user, "Carpeta no encontrada")
            folder_path = folder["path"]

        contents = await file.read()
        if len(contents) > settings.MAX_FILE_SIZE:
            raise ValidationException("El archivo es demasiado grande (máximo 50MB)")

        try:
            object_name = f"{ObjectId()}-{file.filename}"

            await file.seek(0)

            minio_client.put_object(
                settings.BUCKET_NAME,
                object_name,
                data=file.file,
                length=len(contents),
                content_type=file.content_type or "application/octet-stream",
            )

            file_metadata = {
                "filename": file.filename,
                "size": len(contents),
                "upload_date": datetime.utcnow(),
                "file_type": file.content_type or "application/octet-stream",
                "object_name": object_name,
                "folder_id": ObjectId(folder_id) if folder_id else None,
                "path": folder_path,
                "owner": current_user.get("username"),
            }

            result = await file_collection.insert_one(file_metadata)
            created_file = await file_collection.find_one({"_id": result.inserted_id})
            return created_file

        except Exception as e:
            raise InternalServerException(f"Error al subir el archivo: {str(e)}")

    @staticmethod
    async def list_files(current_user: dict, folder_id: Optional[str] = None, search: Optional[str] = None) -> List[dict]:
        query = {}

        if not AuthService.is_admin(current_user):
            query["owner"] = current_user.get("username")

        if folder_id:
            if folder_id == "root":
                query["folder_id"] = None
            else:
                folder_oid = validate_object_id(folder_id, "ID de carpeta")
                query["folder_id"] = folder_oid

        if search:
            query["filename"] = {"$regex": search, "$options": "i"}

        files = await file_collection.find(query).to_list(1000)
        return files

    @staticmethod
    async def get_file(file_id: str, current_user: dict) -> dict:
        file_oid = validate_object_id(file_id, "ID de archivo")
        file_doc = await file_collection.find_one({"_id": file_oid})
        FileService._check_ownership(file_doc, current_user, "Archivo no encontrado")
        return file_doc

    @staticmethod
    async def update_filename(file_id: str, update_data: UpdateFileName, current_user: dict) -> dict:
        file_oid = validate_object_id(file_id, "ID de archivo")
        file_doc = await file_collection.find_one({"_id": file_oid})
        FileService._check_ownership(file_doc, current_user, "Archivo no encontrado")

        update_result = await file_collection.update_one({"_id": file_oid}, {"$set": {"filename": update_data.new_filename}})

        if update_result.matched_count == 0:
            raise NotFoundException("Archivo no encontrado")

        updated_file = await file_collection.find_one({"_id": file_oid})
        return updated_file

    @staticmethod
    async def delete_file(file_id: str, current_user: dict):
        file_oid = validate_object_id(file_id, "ID de archivo")
        file_doc = await file_collection.find_one({"_id": file_oid})
        FileService._check_ownership(file_doc, current_user, "Archivo no encontrado")

        try:
            minio_client.remove_object(settings.BUCKET_NAME, file_doc["object_name"])
            await file_collection.delete_one({"_id": file_oid})
        except Exception as e:
            raise InternalServerException(f"Error al eliminar el archivo: {str(e)}")

    @staticmethod
    def get_file_stream(file_doc: dict):
        try:
            return minio_client.get_object(settings.BUCKET_NAME, file_doc["object_name"])
        except Exception as e:
            raise InternalServerException(f"Error al descargar el archivo: {str(e)}")

    @staticmethod
    async def move_file(file_id: str, folder_id: Optional[str], current_user: dict) -> dict:
        file_oid = validate_object_id(file_id, "ID de archivo")
        file_doc = await file_collection.find_one({"_id": file_oid})
        FileService._check_ownership(file_doc, current_user, "Archivo no encontrado")

        new_folder_path = "/"
        if folder_id and folder_id != "root":
            folder_oid = validate_object_id(folder_id, "ID de carpeta destino")
            folder = await folder_collection.find_one({"_id": folder_oid})
            FileService._check_ownership(folder, current_user, "Carpeta destino no encontrada")
            new_folder_path = folder["path"]
            folder_id = folder_oid
        else:
            folder_id = None

        update_result = await file_collection.update_one({"_id": file_oid}, {"$set": {"folder_id": folder_id, "path": new_folder_path}})

        if update_result.matched_count == 0:
            raise NotFoundException("Archivo no encontrado")

        updated_file = await file_collection.find_one({"_id": file_oid})
        return updated_file

    @staticmethod
    async def copy_file(file_id: str, folder_id: Optional[str], current_user: dict) -> dict:
        file_oid = validate_object_id(file_id, "ID de archivo")
        file_doc = await file_collection.find_one({"_id": file_oid})
        FileService._check_ownership(file_doc, current_user, "Archivo no encontrado")

        new_folder_path = "/"
        if folder_id and folder_id != "root":
            folder_oid = validate_object_id(folder_id, "ID de carpeta destino")
            folder = await folder_collection.find_one({"_id": folder_oid})
            FileService._check_ownership(folder, current_user, "Carpeta destino no encontrada")
            new_folder_path = folder["path"]
            folder_id = folder_oid
        else:
            folder_id = None

        try:
            original_object_name = file_doc["object_name"]
            new_object_name = f"{ObjectId()}-{file_doc['filename']}"

            minio_client.copy_object(settings.BUCKET_NAME, new_object_name, CopySource(settings.BUCKET_NAME, original_object_name))

            new_file_metadata = {
                "filename": file_doc["filename"],
                "size": file_doc["size"],
                "upload_date": datetime.utcnow(),
                "file_type": file_doc["file_type"],
                "object_name": new_object_name,
                "folder_id": folder_id,
                "path": new_folder_path,
                "owner": current_user.get("username"),
            }

            result = await file_collection.insert_one(new_file_metadata)
            copied_file = await file_collection.find_one({"_id": result.inserted_id})
            return copied_file

        except Exception as e:
            raise InternalServerException(f"Error al copiar el archivo: {str(e)}")
