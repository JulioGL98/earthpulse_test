from typing import List, Optional

from fastapi import APIRouter, Depends

from app.middleware.auth import AuthMiddleware
from app.models.folder import CopyFolder, CreateFolder, FolderMetadata, MoveFolder
from app.services.folder_service import FolderService

router = APIRouter(prefix="/folders", tags=["Folders"])


@router.post("", response_model=FolderMetadata, status_code=201)
async def create_folder(folder: CreateFolder, current_user: dict = Depends(AuthMiddleware.get_current_user)):
    """Crea una nueva carpeta"""
    return await FolderService.create_folder(folder, current_user)


@router.get("", response_model=List[FolderMetadata])
async def list_folders(
    parent_folder_id: Optional[str] = None, current_user: dict = Depends(AuthMiddleware.get_current_user)
):
    """Lista carpetas en un directorio específico"""
    return await FolderService.list_folders(current_user, parent_folder_id)


@router.get("/{folder_id}", response_model=FolderMetadata)
async def get_folder(folder_id: str, current_user: dict = Depends(AuthMiddleware.get_current_user)):
    """Obtiene información de una carpeta específica"""
    return await FolderService.get_folder(folder_id, current_user)


@router.get("/{folder_id}/content")
async def get_folder_content(folder_id: str, current_user: dict = Depends(AuthMiddleware.get_current_user)):
    """Obtiene el contenido completo de una carpeta"""
    return await FolderService.get_folder_content(folder_id, current_user)


@router.delete("/{folder_id}", status_code=204)
async def delete_folder(folder_id: str, current_user: dict = Depends(AuthMiddleware.get_current_user)):
    """Elimina una carpeta y todo su contenido"""
    await FolderService.delete_folder(folder_id, current_user)
    return


@router.patch("/{folder_id}/move", response_model=FolderMetadata)
async def move_folder(
    folder_id: str, move_data: MoveFolder, current_user: dict = Depends(AuthMiddleware.get_current_user)
):
    """Mueve una carpeta a otra ubicación"""
    return await FolderService.move_folder(folder_id, move_data.parent_folder_id, current_user)


@router.post("/{folder_id}/copy", response_model=FolderMetadata, status_code=201)
async def copy_folder(
    folder_id: str, copy_data: CopyFolder, current_user: dict = Depends(AuthMiddleware.get_current_user)
):
    """Copia una carpeta a otra ubicación"""
    return await FolderService.copy_folder(folder_id, copy_data.parent_folder_id, current_user)
