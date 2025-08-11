from datetime import datetime

import pytest
from bson import ObjectId
from pydantic import ValidationError

from main import (
    CreateFolder,
    FileMetadata,
    FolderMetadata,
    LoginRequest,
    Token,
    UpdateFileName,
    UserBase,
    UserCreate,
    UserInDB,
)


class TestModels:
    """Tests para modelos Pydantic"""

    def test_file_metadata_valid(self):
        """Test crear FileMetadata válido"""
        file_data = {
            "filename": "test.txt",
            "size": 1024,
            "file_type": "text/plain",
            "object_name": "test-object",
            "owner": "testuser",
        }
        file_obj = FileMetadata(**file_data)
        assert file_obj.filename == "test.txt"
        assert file_obj.size == 1024
        assert file_obj.file_type == "text/plain"
        assert file_obj.object_name == "test-object"
        assert file_obj.owner == "testuser"
        assert isinstance(file_obj.upload_date, datetime)

    def test_folder_metadata_valid(self):
        """Test crear FolderMetadata válido"""
        folder_data = {"name": "Test Folder", "owner": "testuser"}
        folder_obj = FolderMetadata(**folder_data)
        assert folder_obj.name == "Test Folder"
        assert folder_obj.path == "/"
        assert folder_obj.owner == "testuser"
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


class TestUserModels:
    """Tests para modelos de usuario"""

    def test_user_base_valid(self):
        """Test crear UserBase válido"""
        user_data = {"username": "testuser"}
        user_obj = UserBase(**user_data)
        assert user_obj.username == "testuser"

    def test_user_create_valid(self):
        """Test crear UserCreate válido"""
        user_data = {"username": "testuser", "password": "testpassword123"}
        user_obj = UserCreate(**user_data)
        assert user_obj.username == "testuser"
        assert user_obj.password == "testpassword123"

    def test_user_indb_valid(self):
        """Test crear UserInDB válido"""
        user_data = {"username": "testuser", "hashed_password": "hashed_password_string", "role": "user"}
        user_obj = UserInDB(**user_data)
        assert user_obj.username == "testuser"
        assert user_obj.hashed_password == "hashed_password_string"
        assert user_obj.role == "user"
        assert isinstance(user_obj.created_at, datetime)

    def test_token_valid(self):
        """Test crear Token válido"""
        token_data = {"access_token": "fake_token_string", "token_type": "bearer"}
        token_obj = Token(**token_data)
        assert token_obj.access_token == "fake_token_string"
        assert token_obj.token_type == "bearer"

    def test_login_request_valid(self):
        """Test crear LoginRequest válido"""
        login_data = {"username": "testuser", "password": "testpassword123"}
        login_obj = LoginRequest(**login_data)
        assert login_obj.username == "testuser"
        assert login_obj.password == "testpassword123"

    def test_user_username_validation(self):
        """Test validación de username"""
        # Username válido
        user_obj = UserBase(username="testuser")
        assert user_obj.username == "testuser"

        # Username vacío (debería funcionar si no hay validación específica)
        user_obj = UserBase(username="")
        assert user_obj.username == ""

    def test_password_basic(self):
        """Test básico de contraseña"""
        # Contraseña normal
        user_obj = UserCreate(username="testuser", password="testpassword123")
        assert user_obj.password == "testpassword123"

        # Contraseña vacía (debería funcionar si no hay validación específica)
        user_obj = UserCreate(username="testuser", password="")
        assert user_obj.password == ""

    def test_role_values(self):
        """Test valores de rol"""
        # Rol por defecto
        user_obj = UserInDB(username="testuser", hashed_password="hashed")
        assert user_obj.role == "user"

        # Rol admin
        admin_obj = UserInDB(username="admin", hashed_password="hashed", role="admin")
        assert admin_obj.role == "admin"

        # Rol personalizado (debería funcionar si no hay validación específica)
        custom_obj = UserInDB(username="testuser", hashed_password="hashed", role="custom")
        assert custom_obj.role == "custom"
