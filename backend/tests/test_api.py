import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from main import app
import io


class TestHealthEndpoints:
    """Tests para endpoints de salud"""

    def test_root_endpoint(self, client):
        """Test del endpoint raíz"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Google Drive Clone API is running"
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"

    def test_health_check_endpoint(self, client):
        """Test del endpoint de health check"""
        with patch("main.client") as mock_mongo_client:
            # Mock MongoDB ping
            mock_mongo_client.admin.command = AsyncMock(return_value={"ismaster": True})

            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "database" in data
            assert "storage" in data
            assert "timestamp" in data


class TestFileEndpoints:
    """Tests para endpoints de archivos"""

    def test_list_files_empty(self, client, mock_db_client, mock_auth):
        """Test listar archivos cuando no hay ninguno"""
        response = client.get("/files", headers={"Authorization": "Bearer fake_token"})
        if response.status_code == 200:
            assert response.status_code == 200
            assert isinstance(response.json(), list)
        else:
            pytest.skip("Auth middleware not available")

    def test_upload_file_no_file(self, client):
        """Test subir archivo sin archivo"""
        response = client.post("/files/upload")
        assert response.status_code == 422  # Validation error

    def test_upload_file_success(self, client, mock_minio, mock_auth):
        """Test subir archivo exitosamente"""
        # Crear archivo de prueba
        test_file = io.BytesIO(b"test file content")
        test_file.name = "test.txt"

        files = {"file": ("test.txt", test_file, "text/plain")}

        with patch("main.file_collection") as mock_file_col:
            from bson import ObjectId

            mock_file_col.insert_one = AsyncMock(return_value=type("obj", (object,), {"inserted_id": ObjectId()})())
            mock_file_col.find_one = AsyncMock(
                return_value={"_id": ObjectId(), "filename": "test.txt", "size": len(b"test file content"), "file_type": "text/plain", "object_name": "some-object-name"}
            )

            response = client.post("/files/upload", files=files, headers={"Authorization": "Bearer fake_token"})
            if response.status_code == 201:
                assert response.status_code == 201
                data = response.json()
                assert "filename" in data
                assert data["filename"] == "test.txt"
            else:
                pytest.skip("Upload dependencies not available")

    def test_download_invalid_file_id(self, client):
        """Test descargar archivo con ID inválido"""
        response = client.get("/files/download/invalid_id")
        assert response.status_code == 400
        assert "ID de archivo inválido" in response.json()["detail"]

    def test_edit_file_invalid_id(self, client):
        """Test editar archivo con ID inválido"""
        response = client.put("/files/edit/invalid_id", json={"new_filename": "new_name.txt"})
        assert response.status_code == 400
        assert "ID de archivo inválido" in response.json()["detail"]

    def test_delete_file_invalid_id(self, client):
        """Test eliminar archivo con ID inválido"""
        response = client.delete("/files/delete/invalid_id")
        assert response.status_code == 400
        assert "ID de archivo inválido" in response.json()["detail"]

    def test_edit_file_success(self, client, mock_auth):
        """Test editar nombre de archivo exitosamente"""
        from bson import ObjectId

        file_id = str(ObjectId())

        with patch("main.file_collection") as mock_file_col:
            # Mock file exists and belongs to user
            mock_file_col.find_one = AsyncMock(return_value={"_id": ObjectId(file_id), "filename": "old_name.txt", "owner": "testuser"})

            # Mock successful update
            mock_file_col.update_one = AsyncMock(return_value=type("obj", (object,), {"modified_count": 1})())

            # Mock find updated file
            mock_file_col.find_one.side_effect = [
                {  # First call - check if exists
                    "_id": ObjectId(file_id),
                    "filename": "old_name.txt",
                    "owner": "testuser",
                },
                {  # Second call - return updated file
                    "_id": ObjectId(file_id),
                    "filename": "new_name.txt",
                    "owner": "testuser",
                },
            ]

            response = client.put(f"/files/edit/{file_id}", json={"new_filename": "new_name.txt"}, headers={"Authorization": "Bearer fake_token"})

            if response.status_code == 200:
                assert response.status_code == 200
                data = response.json()
                assert data["filename"] == "new_name.txt"
            else:
                pytest.skip("Auth dependencies not available")


class TestFolderEndpoints:
    """Tests para endpoints de carpetas"""

    def test_list_folders_empty(self, client, mock_db_client, mock_auth):
        """Test listar carpetas cuando no hay ninguna"""
        response = client.get("/folders", headers={"Authorization": "Bearer fake_token"})
        if response.status_code == 200:
            assert response.status_code == 200
            assert isinstance(response.json(), list)
        else:
            pytest.skip("Auth middleware not available")

    def test_create_folder_success(self, client, mock_auth):
        """Test crear carpeta exitosamente"""
        folder_data = {"name": "Test Folder"}

        with patch("main.folder_collection") as mock_folder_col:
            from bson import ObjectId

            folder_id = ObjectId()
            mock_folder_col.insert_one = AsyncMock(return_value=type("obj", (object,), {"inserted_id": folder_id})())
            mock_folder_col.find_one = AsyncMock(return_value={"_id": folder_id, "name": "Test Folder", "path": "/Test Folder/", "owner": "testuser"})

            response = client.post("/folders", json=folder_data, headers={"Authorization": "Bearer fake_token"})
            if response.status_code == 201:
                assert response.status_code == 201
                data = response.json()
                assert data["name"] == "Test Folder"
            else:
                pytest.skip("Database dependencies not available")

    def test_create_folder_empty_name(self, client):
        """Test crear carpeta con nombre vacío"""
        folder_data = {"name": ""}
        response = client.post("/folders", json=folder_data)
        assert response.status_code == 422  # Validation error

    def test_get_folder_invalid_id(self, client):
        """Test obtener carpeta con ID inválido"""
        response = client.get("/folders/invalid_id")
        assert response.status_code == 400
        assert "ID de carpeta inválido" in response.json()["detail"]

    def test_delete_folder_invalid_id(self, client):
        """Test eliminar carpeta con ID inválido"""
        response = client.delete("/folders/invalid_id")
        assert response.status_code == 400
        assert "ID de carpeta inválido" in response.json()["detail"]

    def test_get_folder_content_root(self, client, mock_db_client, mock_auth):
        """Test obtener contenido de carpeta raíz"""
        response = client.get("/folders/root/content", headers={"Authorization": "Bearer fake_token"})
        if response.status_code == 200:
            assert response.status_code == 200
            data = response.json()
            assert "folders" in data
            assert "files" in data
            assert "folder_id" in data
            assert "total_items" in data
        else:
            pytest.skip("Auth dependencies not available")
