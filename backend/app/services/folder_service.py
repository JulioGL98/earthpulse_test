from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from minio.api import CopySource

from app.config import settings
from app.database import file_collection, folder_collection, minio_client
from app.models.folder import CreateFolder, FolderMetadata
from app.services.auth_service import AuthService
from app.utils.exceptions import ConflictException, InternalServerException, NotFoundException, ValidationException
from app.utils.validators import validate_object_id


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

    @staticmethod
    async def move_folder(folder_id: str, parent_folder_id: Optional[str], current_user: dict) -> dict:
        """Mueve una carpeta a otra ubicación"""
        folder_oid = validate_object_id(folder_id, "ID de carpeta")
        folder = await folder_collection.find_one({"_id": folder_oid})
        FolderService._check_ownership(folder, current_user, "Carpeta no encontrada")

        # Validar carpeta padre destino si se proporciona
        new_parent_path = "/"
        if parent_folder_id and parent_folder_id != "root":
            parent_oid = validate_object_id(parent_folder_id, "ID de carpeta padre")
            parent_folder = await folder_collection.find_one({"_id": parent_oid})
            FolderService._check_ownership(parent_folder, current_user, "Carpeta padre no encontrada")

            # Verificar que no estemos moviendo una carpeta dentro de sí misma
            if str(parent_oid) == folder_id:
                raise ValidationException("No se puede mover una carpeta dentro de sí misma")

            new_parent_path = parent_folder["path"]
            parent_folder_id = parent_oid
        else:
            parent_folder_id = None

        # Verificar que no exista una carpeta con el mismo nombre en el destino
        existing_folder = await folder_collection.find_one(
            {
                "name": folder["name"],
                "parent_folder_id": parent_folder_id,
                "owner": current_user.get("username"),
                "_id": {"$ne": folder_oid},
            }
        )
        if existing_folder:
            raise ConflictException("Ya existe una carpeta con ese nombre en el destino")

        # Construir nueva ruta
        new_path = f"{new_parent_path.rstrip('/')}/{folder['name']}/"

        # Actualizar carpeta
        update_result = await folder_collection.update_one({"_id": folder_oid}, {"$set": {"parent_folder_id": parent_folder_id, "path": new_path}})

        if update_result.matched_count == 0:
            raise NotFoundException("Carpeta no encontrada")

        # Actualizar rutas de subcarpetas y archivos recursivamente
        await FolderService._update_paths_recursively(folder_oid, new_path)

        updated_folder = await folder_collection.find_one({"_id": folder_oid})
        return updated_folder

    @staticmethod
    async def copy_folder(folder_id: str, parent_folder_id: Optional[str], current_user: dict) -> dict:
        """Copia una carpeta a otra ubicación"""
        folder_oid = validate_object_id(folder_id, "ID de carpeta")
        folder = await folder_collection.find_one({"_id": folder_oid})
        FolderService._check_ownership(folder, current_user, "Carpeta no encontrada")

        # Validar carpeta padre destino si se proporciona
        new_parent_path = "/"
        if parent_folder_id and parent_folder_id != "root":
            parent_oid = validate_object_id(parent_folder_id, "ID de carpeta padre")
            parent_folder = await folder_collection.find_one({"_id": parent_oid})
            FolderService._check_ownership(parent_folder, current_user, "Carpeta padre no encontrada")
            new_parent_path = parent_folder["path"]
            parent_folder_id = parent_oid
        else:
            parent_folder_id = None

        # Generar nombre único si ya existe
        base_name = folder["name"]
        counter = 1
        new_name = base_name
        while await folder_collection.find_one({"name": new_name, "parent_folder_id": parent_folder_id, "owner": current_user.get("username")}):
            new_name = f"{base_name} ({counter})"
            counter += 1

        # Construir nueva ruta
        new_path = f"{new_parent_path.rstrip('/')}/{new_name}/"

        try:
            # Crear nueva carpeta
            new_folder_metadata = {
                "name": new_name,
                "parent_folder_id": parent_folder_id,
                "created_date": datetime.utcnow(),
                "path": new_path,
                "owner": current_user.get("username"),
            }

            result = await folder_collection.insert_one(new_folder_metadata)
            new_folder_id = result.inserted_id

            # Copiar contenido recursivamente
            await FolderService._copy_folder_content(folder_oid, new_folder_id, new_path, current_user)

            copied_folder = await folder_collection.find_one({"_id": new_folder_id})
            return copied_folder

        except Exception as e:
            raise InternalServerException(f"Error al copiar la carpeta: {str(e)}")

    @staticmethod
    async def _update_paths_recursively(folder_id: ObjectId, new_path: str):
        """Actualiza las rutas de subcarpetas y archivos recursivamente"""
        # Actualizar archivos en esta carpeta
        await file_collection.update_many({"folder_id": folder_id}, {"$set": {"path": new_path}})

        # Actualizar subcarpetas
        subfolders = await folder_collection.find({"parent_folder_id": folder_id}).to_list(1000)
        for subfolder in subfolders:
            subfolder_new_path = f"{new_path.rstrip('/')}/{subfolder['name']}/"
            await folder_collection.update_one({"_id": subfolder["_id"]}, {"$set": {"path": subfolder_new_path}})
            # Recursión para subcarpetas
            await FolderService._update_paths_recursively(subfolder["_id"], subfolder_new_path)

    @staticmethod
    async def _copy_folder_content(source_folder_id: ObjectId, dest_folder_id: ObjectId, dest_path: str, current_user: dict):
        """Copia el contenido de una carpeta recursivamente"""
        from app.services.file_service import FileService

        # Copiar archivos
        files = await file_collection.find({"folder_id": source_folder_id}).to_list(1000)
        for file_doc in files:
            try:
                # Copiar archivo en MinIO
                original_object_name = file_doc["object_name"]
                new_object_name = f"{ObjectId()}-{file_doc['filename']}"

                # Usar copy_object con la sintaxis correcta de MinIO
                minio_client.copy_object(settings.BUCKET_NAME, new_object_name, CopySource(settings.BUCKET_NAME, original_object_name))

                # Crear nueva entrada de archivo
                new_file_metadata = {
                    "filename": file_doc["filename"],
                    "size": file_doc["size"],
                    "upload_date": datetime.utcnow(),
                    "file_type": file_doc["file_type"],
                    "object_name": new_object_name,
                    "folder_id": dest_folder_id,
                    "path": dest_path,
                    "owner": current_user.get("username"),
                }
                await file_collection.insert_one(new_file_metadata)
            except Exception:
                continue  # Si falla un archivo, continuar con los demás

        # Copiar subcarpetas recursivamente
        subfolders = await folder_collection.find({"parent_folder_id": source_folder_id}).to_list(1000)
        for subfolder in subfolders:
            subfolder_new_path = f"{dest_path.rstrip('/')}/{subfolder['name']}/"

            # Crear subcarpeta
            new_subfolder_metadata = {
                "name": subfolder["name"],
                "parent_folder_id": dest_folder_id,
                "created_date": datetime.utcnow(),
                "path": subfolder_new_path,
                "owner": current_user.get("username"),
            }
            result = await folder_collection.insert_one(new_subfolder_metadata)
            new_subfolder_id = result.inserted_id

            # Copiar contenido de la subcarpeta
            await FolderService._copy_folder_content(subfolder["_id"], new_subfolder_id, subfolder_new_path, current_user)
