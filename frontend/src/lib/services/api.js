import { get } from 'svelte/store';
import { authToken, API_URL } from '$lib/stores/auth';

export async function authFetch(url, options = {}) {
    const token = get(authToken);
    const headers = { ...(options.headers || {}) };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return fetch(url, { ...options, headers });
}

export async function login(username, password) {
    const resp = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
    });
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || 'Error de autenticación');
    }
    return resp.json();
}

export async function register(username, password) {
    const resp = await fetch(`${API_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
    });
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || 'Error de autenticación');
    }
    return resp.json();
}

export async function getFolderContent(folderId = 'root') {
    const response = await authFetch(`${API_URL}/folders/${folderId}/content`);
    if (!response.ok) throw new Error('Error al cargar el contenido de la carpeta.');
    return response.json();
}

export async function searchFiles(term, folderId) {
    const params = new URLSearchParams({
        search: term,
        ...(folderId && folderId !== 'root' && { folder_id: folderId }),
    });
    const response = await authFetch(`${API_URL}/files?${params}`);
    if (!response.ok) throw new Error('Error en la búsqueda.');
    return response.json();
}

export async function getFolderDetails(folderId) {
    const response = await authFetch(`${API_URL}/folders/${folderId}`);
    if (response.ok) {
        return response.json();
    }
    return null;
}

export async function createFolder(name, parentFolderId) {
    const folderData = {
        name: name,
        parent_folder_id: parentFolderId === 'root' || !parentFolderId ? null : parentFolderId,
    };
    const response = await authFetch(`${API_URL}/folders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(folderData),
    });
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error al crear la carpeta.');
    }
    return response.json();
}

export async function deleteFolder(folderId) {
    const response = await authFetch(`${API_URL}/folders/${folderId}`, { method: 'DELETE' });
    if (!response.ok) throw new Error('Error al eliminar la carpeta.');
    // Las respuestas 204 No Content no tienen JSON
    if (response.status === 204) return {};
    return response.json();
}

export function uploadFileWithProgress(file, folderId, onProgress) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        const formData = new FormData();

        formData.append('file', file);
        if (folderId && folderId !== 'root') formData.append('folder_id', folderId);

        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const progress = Math.round((e.loaded / e.total) * 100);
                onProgress(progress);
            }
        });

        xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    resolve(response);
                } catch {
                    reject(new Error('Error parsing server response'));
                }
            } else {
                try {
                    const errorResponse = JSON.parse(xhr.responseText);
                    reject(new Error(errorResponse.detail || `Error ${xhr.status}: ${xhr.statusText}`));
                } catch {
                    reject(new Error(`HTTP Error ${xhr.status}: ${xhr.statusText}`));
                }
            }
        });

        xhr.addEventListener('error', () => reject(new Error('Error de red durante la subida')));
        xhr.addEventListener('abort', () => reject(new Error('Subida cancelada')));
        xhr.addEventListener('timeout', () => reject(new Error('Tiempo de espera agotado')));

        xhr.timeout = 30000;
        xhr.open('POST', `${API_URL}/files/upload`);
        const token = get(authToken);
        if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);
        xhr.send(formData);
    });
}

export async function deleteFile(fileId) {
    const response = await authFetch(`${API_URL}/files/delete/${fileId}`, { method: 'DELETE' });
    if (!response.ok) throw new Error('Error al eliminar el archivo.');
    // Las respuestas 204 No Content no tienen JSON
    if (response.status === 204) return {};
    return response.json();
}

export async function renameFile(fileId, newFilename) {
    const response = await authFetch(`${API_URL}/files/edit/${fileId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_filename: newFilename }),
    });
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error al actualizar el nombre del archivo.');
    }
    return response.json();
}

export async function downloadFile(fileId, filename) {
    const resp = await authFetch(`${API_URL}/files/download/${fileId}`);
    if (!resp.ok) throw new Error('Error al descargar el archivo');

    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    URL.revokeObjectURL(url);
}

export async function getFilePreviewContent(file) {
    const fileType = file.file_type.toLowerCase();
    if (fileType.startsWith('image/') || fileType === 'application/pdf') {
        const resp = await authFetch(`${API_URL}/files/download/${file._id}?inline=true`);
        if (!resp.ok) throw new Error('No se pudo cargar la vista previa');
        const blob = await resp.blob();
        return URL.createObjectURL(blob);
    }
    if (fileType.startsWith('text/') || fileType.includes('json') || fileType.includes('javascript')) {
        const resp = await authFetch(`${API_URL}/files/download/${file._id}`);
        if (!resp.ok) throw new Error('Error al cargar el archivo');
        return resp.text();
    }
    throw new Error('Tipo de archivo no soportado para previsualización');
}

export async function moveFile(fileId, targetFolderId) {
    const response = await authFetch(`${API_URL}/files/${fileId}/move`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder_id: targetFolderId }),
    });
    if (!response.ok) throw new Error('Error al mover archivo');
    return response.json();
}

export async function copyFile(fileId, targetFolderId) {
    const response = await authFetch(`${API_URL}/files/${fileId}/copy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder_id: targetFolderId }),
    });
    if (!response.ok) throw new Error('Error al copiar archivo');
    return response.json();
}

export async function moveFolder(folderId, targetFolderId) {
    const response = await authFetch(`${API_URL}/folders/${folderId}/move`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ parent_folder_id: targetFolderId }),
    });
    if (!response.ok) throw new Error('Error al mover carpeta');
    return response.json();
}

export async function copyFolder(folderId, targetFolderId) {
    const response = await authFetch(`${API_URL}/folders/${folderId}/copy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ parent_folder_id: targetFolderId }),
    });
    if (!response.ok) throw new Error('Error al copiar carpeta');
    return response.json();
}

export async function getFolders(parentFolderId = 'root') {
    const response = await authFetch(`${API_URL}/folders?parent_folder_id=${parentFolderId}`);
    if (!response.ok) throw new Error('Error al cargar carpetas');
    return response.json();
}
