import pytest
import asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient
from unittest.mock import AsyncMock, patch, MagicMock
from main import app
import os
from bson import ObjectId

# Configuración de base de datos de prueba
TEST_DATABASE_URL = "mongodb://localhost:27017/test_file_management"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def client():
    """Fixture para cliente de pruebas síncronas"""
    # Mock the startup event to avoid database connections
    with patch("main.create_bucket_if_not_exists"), patch("main.user_collection") as mock_user_col:
        # Mock admin user check
        mock_user_col.find_one = AsyncMock(return_value={"username": "admin", "role": "admin"})
        mock_user_col.insert_one = AsyncMock()
        mock_user_col.update_one = AsyncMock()

        with TestClient(app) as c:
            yield c


@pytest.fixture
def mock_db_client():
    """Mock para cliente de base de datos"""
    with patch("main.file_collection") as mock_file_col, patch("main.folder_collection") as mock_folder_col, patch("main.user_collection") as mock_user_col:
        # Configurar mocks para retornar listas vacías por defecto
        mock_file_col.find.return_value.to_list = AsyncMock(return_value=[])
        mock_folder_col.find.return_value.to_list = AsyncMock(return_value=[])
        mock_user_col.find.return_value.to_list = AsyncMock(return_value=[])

        # Mock find_one para retornar None por defecto
        mock_file_col.find_one = AsyncMock(return_value=None)
        mock_folder_col.find_one = AsyncMock(return_value=None)
        mock_user_col.find_one = AsyncMock(return_value=None)

        yield {"file_collection": mock_file_col, "folder_collection": mock_folder_col, "user_collection": mock_user_col}


@pytest.fixture
def mock_minio():
    """Mock para cliente MinIO"""
    with patch("main.minio_client") as mock_minio_client:
        # Configure common MinIO operations
        mock_minio_client.bucket_exists.return_value = True
        mock_minio_client.make_bucket = MagicMock()
        mock_minio_client.put_object = MagicMock()
        mock_minio_client.get_object = MagicMock()
        mock_minio_client.remove_object = MagicMock()

        yield mock_minio_client


@pytest.fixture
def mock_auth():
    """Mock para funciones de autenticación"""
    with (
        patch("main.get_current_user") as mock_get_user,
        patch("main.verify_password") as mock_verify_password,
        patch("main.get_password_hash") as mock_get_hash,
        patch("main.create_access_token") as mock_create_token,
    ):
        # Configure default user
        mock_get_user.return_value = {"_id": ObjectId(), "username": "testuser", "email": "test@example.com", "role": "user"}

        mock_verify_password.return_value = True
        mock_get_hash.return_value = "hashed_password"
        mock_create_token.return_value = "fake_token"

        yield {"get_current_user": mock_get_user, "verify_password": mock_verify_password, "get_password_hash": mock_get_hash, "create_access_token": mock_create_token}


@pytest.fixture
async def async_client():
    """Fixture para cliente de pruebas asíncronas"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_db():
    """Fixture para base de datos de prueba"""
    client = AsyncIOMotorClient(TEST_DATABASE_URL)
    db = client.test_file_management
    yield db
    # Cleanup después de las pruebas
    try:
        await client.drop_database("test_file_management")
    except Exception:
        pass  # Ignore cleanup errors in tests
    client.close()


@pytest.fixture
def sample_file_data():
    """Datos de archivo de muestra para pruebas"""
    return {"filename": "test_file.txt", "content": b"This is a test file content", "content_type": "text/plain"}


@pytest.fixture
def sample_folder_data():
    """Datos de carpeta de muestra para pruebas"""
    return {"name": "Test Folder", "parent_folder_id": None}


@pytest.fixture
def sample_user_data():
    """Datos de usuario de muestra para pruebas"""
    return {"username": "testuser", "email": "test@example.com", "password": "testpassword123"}


@pytest.fixture
def mock_object_id():
    """Fixture para generar ObjectIds consistentes"""
    return ObjectId("507f1f77bcf86cd799439011")
