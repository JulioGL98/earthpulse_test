import pytest
import asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient
from unittest.mock import AsyncMock, patch
from main import app
import os

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
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_db_client():
    """Mock para cliente de base de datos"""
    with patch("main.file_collection") as mock_file_col, patch("main.folder_collection") as mock_folder_col:
        # Configurar mocks para retornar listas vacías por defecto
        mock_file_col.find.return_value.to_list = AsyncMock(return_value=[])
        mock_folder_col.find.return_value.to_list = AsyncMock(return_value=[])

        yield {"file_collection": mock_file_col, "folder_collection": mock_folder_col}


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
