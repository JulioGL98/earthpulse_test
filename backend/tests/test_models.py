import pytest
from pydantic import ValidationError
from main import FileMetadata, FolderMetadata, CreateFolder, UpdateFileName
from datetime import datetime
from bson import ObjectId


class TestModels:
    """Tests para modelos Pydantic"""

    def test_file_metadata_valid(self):
        """Test crear FileMetadata válido"""
        file_data = {
            "filename": "test.txt",
            "size": 1024,
            "file_type": "text/plain",
            "object_name": "test-object",
        }
        file_obj = FileMetadata(**file_data)
        assert file_obj.filename == "test.txt"
        assert file_obj.size == 1024
        assert file_obj.file_type == "text/plain"
        assert file_obj.object_name == "test-object"
        assert isinstance(file_obj.upload_date, datetime)

    def test_folder_metadata_valid(self):
        """Test crear FolderMetadata válido"""
        folder_data = {
            "name": "Test Folder",
        }
        folder_obj = FolderMetadata(**folder_data)
        assert folder_obj.name == "Test Folder"
        assert folder_obj.path == "/"
        assert isinstance(folder_obj.created_date, datetime)

    def test_create_folder_valid(self):
        """Test crear CreateFolder válido"""
        folder_data = {
            "name": "New Folder",
        }
        folder_obj = CreateFolder(**folder_data)
        assert folder_obj.name == "New Folder"
        assert folder_obj.parent_folder_id is None

    def test_create_folder_with_parent(self):
        """Test crear CreateFolder con carpeta padre"""
        parent_id = str(ObjectId())
        folder_data = {
            "name": "Child Folder",
            "parent_folder_id": parent_id,
        }
        folder_obj = CreateFolder(**folder_data)
        assert folder_obj.name == "Child Folder"
        assert folder_obj.parent_folder_id == parent_id

    def test_update_filename_valid(self):
        """Test crear UpdateFileName válido"""
        update_data = {
            "new_filename": "updated_file.txt",
        }
        update_obj = UpdateFileName(**update_data)
        assert update_obj.new_filename == "updated_file.txt"

    def test_update_filename_empty(self):
        """Test crear UpdateFileName con nombre vacío"""
        with pytest.raises(ValidationError):
            UpdateFileName(new_filename="")

    def test_update_filename_too_long(self):
        """Test crear UpdateFileName con nombre muy largo"""
        long_name = "a" * 256  # Más de 255 caracteres
        with pytest.raises(ValidationError):
            UpdateFileName(new_filename=long_name)

    def test_folder_name_too_long(self):
        """Test crear CreateFolder con nombre muy largo"""
        long_name = "a" * 101  # Más de 100 caracteres
        with pytest.raises(ValidationError):
            CreateFolder(name=long_name)

    def test_folder_name_empty(self):
        """Test crear CreateFolder con nombre vacío"""
        with pytest.raises(ValidationError):
            CreateFolder(name="")
