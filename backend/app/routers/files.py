from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from app.middleware.auth import AuthMiddleware
from app.models.file import CopyFile, FileMetadata, MoveFile, UpdateFileName
from app.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["Files"])


@router.post("/upload", response_model=FileMetadata, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    folder_id: Optional[str] = Form(None),
    current_user: dict = Depends(AuthMiddleware.get_current_user),
):
    return await FileService.upload_file(file, current_user, folder_id)


@router.get("", response_model=List[FileMetadata])
async def list_files(
    folder_id: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(AuthMiddleware.get_current_user),
):
    return await FileService.list_files(current_user, folder_id, search)


@router.get("/download/{file_id}")
async def download_file(
    file_id: str, inline: Optional[bool] = False, current_user: dict = Depends(AuthMiddleware.get_current_user)
):
    file_doc = await FileService.get_file(file_id, current_user)
    response = FileService.get_file_stream(file_doc)

    headers = {}
    if inline and file_doc["file_type"] in [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/svg+xml",
    ]:
        headers["Content-Disposition"] = f"inline; filename={file_doc['filename']}"
    else:
        headers["Content-Disposition"] = f"attachment; filename={file_doc['filename']}"

    return StreamingResponse(response.stream(32 * 1024), media_type=file_doc["file_type"], headers=headers)


@router.put("/edit/{file_id}", response_model=FileMetadata)
async def edit_file_name(
    file_id: str, file_update: UpdateFileName, current_user: dict = Depends(AuthMiddleware.get_current_user)
):
    return await FileService.update_filename(file_id, file_update, current_user)


@router.delete("/delete/{file_id}", status_code=204)
async def delete_file(file_id: str, current_user: dict = Depends(AuthMiddleware.get_current_user)):
    await FileService.delete_file(file_id, current_user)
    return


@router.patch("/{file_id}/move", response_model=FileMetadata)
async def move_file(file_id: str, move_data: MoveFile, current_user: dict = Depends(AuthMiddleware.get_current_user)):
    return await FileService.move_file(file_id, move_data.folder_id, current_user)


@router.post("/{file_id}/copy", response_model=FileMetadata, status_code=201)
async def copy_file(file_id: str, copy_data: CopyFile, current_user: dict = Depends(AuthMiddleware.get_current_user)):
    return await FileService.copy_file(file_id, copy_data.folder_id, current_user)
