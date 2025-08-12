from typing import List, Optional
from fastapi import APIRouter, Depends
from app.models.folder import FolderMetadata, CreateFolder
from app.services.folder_service import FolderService
from app.middleware.auth import AuthMiddleware

router = APIRouter(prefix="/folders", tags=["Folders"])


@router.post("", response_model=FolderMetadata, status_code=201)
async def create_folder(folder: CreateFolder, current_user: dict = Depends(AuthMiddleware.get_current_user)):
    """Crea una nueva carpeta"""
    return await FolderService.create_folder(folder, current_user)


@router.get("", response_model=List[FolderMetadata])
async def list_folders(parent_folder_id: Optional[str] = None, current_user: dict = Depends(AuthMiddleware.get_current_user)):
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
