from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from app.database import folder_collection, file_collection, minio_client
from app.config import settings
from app.models.folder import FolderMetadata, CreateFolder
from app.utils.validators import validate_object_id
from app.utils.exceptions import NotFoundException, ValidationException, ConflictException, InternalServerException
from app.services.auth_service import AuthService


class FolderService:
    """Servicio para manejo de carpetas"""

    @staticmethod
    def _check_ownership(resource: Optional[dict], current_user: dict, not_found_message: str = "Recurso no encontrado"):
        """Verifica permisos de acceso a un recurso"""
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
    async def create_folder(folder_data: CreateFolder, current_user: dict) -> dict:
        """Crea una nueva carpeta"""
        # Validar que no exista una carpeta con el mismo nombre en el mismo directorio
        query = {"name": folder_data.name, "owner": current_user.get("username")}
        if folder_data.parent_folder_id:
            parent_oid = validate_object_id(folder_data.parent_folder_id, "ID de carpeta padre")
            query["parent_folder_id"] = parent_oid
        else:
            query["parent_folder_id"] = None

        existing_folder = await folder_collection.find_one(query)
        if existing_folder:
            raise ConflictException("Ya existe una carpeta con ese nombre en este directorio")

        # Validar carpeta padre si se proporciona
        parent_path = "/"
        if folder_data.parent_folder_id:
            parent_folder = await folder_collection.find_one({"_id": parent_oid})
            FolderService._check_ownership(parent_folder, current_user, "Carpeta padre no encontrada")
            parent_path = parent_folder["path"]

        # Construir ruta completa
        new_path = f"{parent_path.rstrip('/')}/{folder_data.name}/"

        folder_metadata = {
            "name": folder_data.name,
            "parent_folder_id": ObjectId(folder_data.parent_folder_id) if folder_data.parent_folder_id else None,
            "created_date": datetime.utcnow(),
            "path": new_path,
            "owner": current_user.get("username"),
        }

        result = await folder_collection.insert_one(folder_metadata)
        created_folder = await folder_collection.find_one({"_id": result.inserted_id})
        return created_folder

    @staticmethod
    async def list_folders(current_user: dict, parent_folder_id: Optional[str] = None) -> List[dict]:
        """Lista carpetas en un directorio específico"""
        query = {}

        # Filtrar por ownership a menos que sea admin
        if not AuthService.is_admin(current_user):
            query["owner"] = current_user.get("username")

        if parent_folder_id:
            if parent_folder_id == "root":
                query["parent_folder_id"] = None
            else:
                parent_oid = validate_object_id(parent_folder_id, "ID de carpeta")
                query["parent_folder_id"] = parent_oid
        else:
            query["parent_folder_id"] = None

        folders = await folder_collection.find(query).to_list(1000)
        return folders

    @staticmethod
    async def get_folder(folder_id: str, current_user: dict) -> dict:
        """Obtiene información de una carpeta específica"""
        folder_oid = validate_object_id(folder_id, "ID de carpeta")
        folder = await folder_collection.find_one({"_id": folder_oid})
        FolderService._check_ownership(folder, current_user, "Carpeta no encontrada")
        return folder

    @staticmethod
    async def get_folder_content(folder_id: str, current_user: dict) -> dict:
        """Obtiene el contenido completo de una carpeta"""
        # Base queries para carpetas y archivos
        base_folder_query = {"parent_folder_id": None if folder_id == "root" else validate_object_id(folder_id, "ID de carpeta")}
        base_file_query = {"folder_id": None if folder_id == "root" else validate_object_id(folder_id, "ID de carpeta")}

        # Filtrar por ownership a menos que sea admin
        if not AuthService.is_admin(current_user):
            base_folder_query["owner"] = current_user.get("username")
            base_file_query["owner"] = current_user.get("username")

        # Obtener carpetas y archivos
        folders = await folder_collection.find(base_folder_query).to_list(1000)
        files = await file_collection.find(base_file_query).to_list(1000)

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

    @staticmethod
    async def delete_folder(folder_id: str, current_user: dict):
        """Elimina una carpeta y todo su contenido recursivamente"""
        folder_oid = validate_object_id(folder_id, "ID de carpeta")
        folder = await folder_collection.find_one({"_id": folder_oid})
        FolderService._check_ownership(folder, current_user, "Carpeta no encontrada")

        try:
            # Eliminar archivos en la carpeta
            files_in_folder = await file_collection.find({"folder_id": folder_oid}).to_list(1000)
            for file_doc in files_in_folder:
                minio_client.remove_object(settings.BUCKET_NAME, file_doc["object_name"])
                await file_collection.delete_one({"_id": file_doc["_id"]})

            # Eliminar subcarpetas recursivamente
            subfolders = await folder_collection.find({"parent_folder_id": folder_oid}).to_list(1000)
            for subfolder in subfolders:
                await FolderService.delete_folder(str(subfolder["_id"]), current_user)

            # Eliminar la carpeta
            await folder_collection.delete_one({"_id": folder_oid})

        except Exception as e:
            raise InternalServerException(f"Error al eliminar la carpeta: {str(e)}")
