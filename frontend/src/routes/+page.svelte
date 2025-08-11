<script>
  import { onMount, onDestroy } from 'svelte';
  import { writable } from 'svelte/store';

  // --- Auth State ---
  let authToken = writable(null);
  let authUser = writable(null);
  let showAuthScreen = writable(true); // Mostrar login/registro por defecto hasta validar token
  let authMode = writable('login'); // 'login' | 'register'
  let authUsername = writable('');
  let authPassword = writable('');
  let authError = writable('');
  let authLoading = writable(false);

  const API_URL = 'http://localhost:8000';

  function saveToken(token) {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('auth_token', token);
    }
    authToken.set(token);
  }
  function loadToken() {
    if (typeof localStorage !== 'undefined') {
      const t = localStorage.getItem('auth_token');
      if (t) authToken.set(t);
    }
  }
  function logout() {
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem('auth_token');
    }
    authToken.set(null);
    authUser.set(null);
    showAuthScreen.set(true);
  }
  // Función para manejar la tecla Enter en los campos de entrada
  function handleKeyPress(event) {
    if (event.key === 'Enter') {
      event.preventDefault();
      handleAuthSubmit();
    }
  }

  async function handleAuthSubmit() {
    authError.set('');
    if (!$authUsername.trim() || !$authPassword.trim()) {
      authError.set('Usuario y contraseña requeridos');
      return;
    }
    authLoading.set(true);
    try {
      const endpoint = $authMode === 'login' ? '/auth/login' : '/auth/register';
      const resp = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: $authUsername.trim(), password: $authPassword }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || 'Error de autenticación');
      }
      const data = await resp.json();
      if (data.access_token) {
        saveToken(data.access_token);
        authUser.set($authUsername.trim());
        showAuthScreen.set(false);
        // limpiar campos
        authPassword.set('');
        // CARGAR CONTENIDO INMEDIATAMENTE DESPUÉS DEL LOGIN EXITOSO
        await loadFolderContent('root');
      } else {
        throw new Error('Token no recibido');
      }
    } catch (e) {
      authError.set(e.message);
    } finally {
      authLoading.set(false);
    }
  }

  // --- Interceptor fetch helper con token ---
  async function authFetch(url, options = {}) {
    const token = $authToken;
    const headers = { ...(options.headers || {}) };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return fetch(url, { ...options, headers });
  }

  // Verificar token rápidamente (intentando un endpoint protegido)
  onMount(async () => {
    loadToken(); // ahora seguro en cliente
    if ($authToken) {
      try {
        const resp = await authFetch(`${API_URL}/files`);
        if (resp.ok) {
          authUser.set(''); // Username no viaja en token simple; podríamos decodificarlo
          showAuthScreen.set(false);
          await loadFolderContent('root');
        } else {
          logout();
        }
      } catch {
        logout();
      }
    } else {
      isLoading.set(false);
    }
  });

  // --- Estado de la Aplicación Existente ---
  let files = writable([]);
  let folders = writable([]);
  let currentFolder = writable('root');
  let folderPath = writable('/');
  let folderHistory = writable([]); // Para navegar hacia atrás
  let currentFolderInfo = writable(null); // Información de la carpeta actual
  let isLoading = writable(true);
  let errorMessage = writable('');
  let successMessage = writable('');
  let uploadProgress = writable(null); // { fileName: string, progress: number, totalFiles: number, currentFile: number }
  let editingFileId = writable(null);
  let editingFolderId = writable(null);
  let newFileName = writable('');
  let originalFileName = writable(''); // Para comparar si el nombre cambió
  let newFolderName = writable('');
  let searchTerm = writable('');
  let sortBy = writable('name');
  let sortOrder = writable('asc');
  let viewMode = writable('list'); // 'list' or 'grid'
  let showCreateFolder = writable(false);

  // --- Variables para selección múltiple ---
  let selectedFiles = writable(new Set());
  let selectedFolders = writable(new Set());
  let selectAll = writable(false);
  let showBulkActions = writable(false);

  // --- Variables para preview ---
  let showPreview = writable(false);
  let previewFile = writable(null);
  let previewContent = writable('');
  let previewError = writable('');

  // --- Variables para selector de carpeta ---
  let showFolderSelector = writable(false);
  let allFolders = writable([]);
  let selectorCurrentFolder = writable('root');
  let selectedTargetFolder = writable(null);
  let selectorMode = writable('move'); // 'move' o 'copy'

  // Reemplazar fetch directos por authFetch
  async function loadFolderContent(folderId = 'root') {
    if ($showAuthScreen) return;
    isLoading.set(true);
    errorMessage.set('');

    // Limpiar cache de miniaturas al cambiar de carpeta
    clearThumbnailCache();

    try {
      const response = await authFetch(`${API_URL}/folders/${folderId}/content`);
      if (!response.ok) throw new Error('Error al cargar el contenido de la carpeta.');
      const data = await response.json();
      files.set(data.files);
      folders.set(data.folders);
      currentFolder.set(folderId);
    } catch (error) {
      errorMessage.set(error.message);
    } finally {
      isLoading.set(false);
    }
  }

  /**
   * Carga archivos con filtros de búsqueda
   */
  async function searchFiles() {
    if ($showAuthScreen) return;
    if (!$searchTerm.trim()) {
      await loadFolderContent($currentFolder || 'root');
      return;
    }
    isLoading.set(true);
    try {
      const params = new URLSearchParams({
        search: $searchTerm,
        ...($currentFolder && $currentFolder !== 'root' && { folder_id: $currentFolder }),
      });
      const response = await authFetch(`${API_URL}/files?${params}`);
      if (!response.ok) throw new Error('Error en la búsqueda.');
      const data = await response.json();
      files.set(data);
    } catch (error) {
      errorMessage.set(error.message);
    } finally {
      isLoading.set(false);
    }
  }

  /**
   * Navega a una carpeta específica
   */
  async function navigateToFolder(folderId) {
    // Guardar la carpeta actual en el historial si no es la misma
    if ($currentFolder !== folderId && $currentFolder !== 'root') {
      folderHistory.update((h) => [...h, { id: $currentFolder, info: $currentFolderInfo }]);
    }
    await loadFolderContent(folderId);
    // Actualizar la ruta de navegación y información de la carpeta actual
    if (folderId === 'root' || !folderId) {
      folderPath.set('/');
      currentFolderInfo.set(null);
    } else {
      try {
        const response = await authFetch(`${API_URL}/folders/${folderId}`);
        if (response.ok) {
          const folder = await response.json();
          folderPath.set(folder.path);
          currentFolderInfo.set(folder);
        }
      } catch {}
    }
  }

  /**
   * Navega hacia atrás en la jerarquía de carpetas
   */
  async function navigateBack() {
    if ($currentFolderInfo && $currentFolderInfo.parent_folder_id) {
      const parentId = $currentFolderInfo.parent_folder_id;
      await navigateToFolder(parentId || 'root');
    } else {
      // Si estamos en una subcarpeta pero no tenemos parent_folder_id, ir a root
      await navigateToFolder('root');
    }
  }

  /**
   * Crea una nueva carpeta
   */
  async function createFolder() {
    if (!$newFolderName.trim()) {
      errorMessage.set('El nombre de la carpeta no puede estar vacío.');
      setTimeout(() => errorMessage.set(''), 3000);
      return;
    }
    try {
      const folderData = {
        name: $newFolderName,
        parent_folder_id: $currentFolder === 'root' || !$currentFolder ? null : $currentFolder,
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
      successMessage.set('Carpeta creada con éxito.');
      newFolderName.set('');
      showCreateFolder.set(false);
      await loadFolderContent($currentFolder || 'root');
    } catch (error) {
      errorMessage.set(error.message);
    } finally {
      setTimeout(() => {
        successMessage.set('');
        errorMessage.set('');
      }, 3000);
    }
  }

  /**
   * Elimina una carpeta
   */
  async function deleteFolder(folderId) {
    if (!confirm('¿Estás seguro de que quieres eliminar esta carpeta y todo su contenido?')) return;
    try {
      const response = await authFetch(`${API_URL}/folders/${folderId}`, { method: 'DELETE' });
      if (!response.ok) throw new Error('Error al eliminar la carpeta.');
      successMessage.set('Carpeta eliminada con éxito.');
      await loadFolderContent($currentFolder || 'root');
    } catch (error) {
      errorMessage.set(error.message);
    } finally {
      setTimeout(() => successMessage.set(''), 3000);
    }
  }

  /**
   * Sube un archivo individual con seguimiento de progreso
   */
  function uploadFileWithProgress(file, folderId = null) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const formData = new FormData();

      formData.append('file', file);
      if (folderId && folderId !== 'root') formData.append('folder_id', folderId);

      // Configurar el seguimiento de progreso
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const progress = Math.round((e.loaded / e.total) * 100);
          uploadProgress.update((c) => ({ ...c, progress: Math.min(progress, 100) }));
        }
      });

      // Cuando la subida se completa (pero puede estar procesándose)
      xhr.upload.addEventListener('load', () => {
        uploadProgress.update((c) => ({ ...c, progress: 100 }));
      });

      // Configurar manejadores de eventos para la respuesta
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

      xhr.addEventListener('error', () => {
        reject(new Error('Error de red durante la subida'));
      });

      xhr.addEventListener('abort', () => {
        reject(new Error('Subida cancelada'));
      });

      xhr.addEventListener('timeout', () => {
        reject(new Error('Tiempo de espera agotado'));
      });

      // Configurar timeout (30 segundos)
      xhr.timeout = 30000;

      // Iniciar la subida
      xhr.open('POST', `${API_URL}/files/upload`);
      const token = $authToken;
      if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      xhr.send(formData);
    });
  }

  /**
   * Maneja la subida de archivos
   */
  async function handleFileUpload(e) {
    const filesArr = Array.from(e.target.files || e.dataTransfer?.files || []);
    if (filesArr.length === 0) return;

    // Obtener el valor actual de la carpeta INMEDIATAMENTE
    const currentFolderValue = $currentFolder;

    isLoading.set(true);
    successMessage.set('');
    errorMessage.set('');

    let uploadedCount = 0;

    try {
      // Subir archivos uno por uno con progreso
      for (let i = 0; i < filesArr.length; i++) {
        const file = filesArr[i];

        // Inicializar el estado de progreso
        uploadProgress.set({
          fileName: file.name,
          progress: 0,
          totalFiles: filesArr.length,
          currentFile: i + 1,
        });

        // Subir archivo con seguimiento de progreso
        await uploadFileWithProgress(file, currentFolderValue);
        uploadedCount++;

        // Pequeña pausa entre archivos para mejor UX (excepto en el último)
        if (i < filesArr.length - 1) await new Promise((r) => setTimeout(r, 500));
      }

      // Limpiar estado de progreso
      uploadProgress.set(null);

      successMessage.set(
        `¡${uploadedCount} archivo${uploadedCount > 1 ? 's' : ''} subido${uploadedCount > 1 ? 's' : ''} con éxito!`
      );
      await loadFolderContent(currentFolderValue || 'root');
    } catch (error) {
      uploadProgress.set(null);
      const failedMessage =
        uploadedCount > 0
          ? `${uploadedCount} archivos subidos. Error en: ${error.message}`
          : `Error al subir archivo: ${error.message}`;
      errorMessage.set(failedMessage);
    } finally {
      // Limpiar el input file para permitir subir el mismo archivo otra vez
      const fileInput = document.getElementById('file-upload');
      if (fileInput) fileInput.value = '';

      isLoading.set(false);
      setTimeout(() => {
        successMessage.set('');
        errorMessage.set('');
      }, 3000);
    }
  }

  /**
   * Maneja la eliminación de un archivo
   */
  async function handleDeleteFile(fileId) {
    if (!confirm('¿Estás seguro de que quieres eliminar este archivo?')) return;
    try {
      const response = await authFetch(`${API_URL}/files/delete/${fileId}`, { method: 'DELETE' });
      if (!response.ok) throw new Error('Error al eliminar el archivo.');
      successMessage.set('Archivo eliminado con éxito.');
      files.update((cf) => cf.filter((f) => f._id !== fileId));
    } catch (error) {
      errorMessage.set(error.message);
    } finally {
      setTimeout(() => successMessage.set(''), 3000);
    }
  }

  /**
   * Funciones de edición
   */
  function startEditingFile(file) {
    editingFileId.set(file._id);
    newFileName.set(file.filename);
    originalFileName.set(file.filename);
  }
  function cancelEditing() {
    editingFileId.set(null);
    editingFolderId.set(null);
    newFileName.set('');
    originalFileName.set('');
    newFolderName.set('');
  }
  async function saveFileName(fileId, forceValidation = false) {
    const trimmedName = $newFileName.trim();
    const originalName = $originalFileName.trim();
    if (trimmedName === originalName && !forceValidation) {
      cancelEditing();
      return;
    }
    if (!trimmedName) {
      if (forceValidation) {
        errorMessage.set('El nombre del archivo no puede estar vacío.');
        setTimeout(() => errorMessage.set(''), 3000);
      } else {
        newFileName.set(originalName);
      }
      return;
    }
    try {
      const response = await authFetch(`${API_URL}/files/edit/${fileId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_filename: trimmedName }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error al actualizar el nombre del archivo.');
      }
      await loadFolderContent($currentFolder || 'root');
      cancelEditing();
      successMessage.set('Nombre del archivo actualizado con éxito.');
      setTimeout(() => successMessage.set(''), 3000);
    } catch (error) {
      errorMessage.set(error.message);
    }
  }
  function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  }
  function formatDate(dateString) {
    const options = {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    };
    return new Date(dateString).toLocaleDateString(undefined, options);
  }
  function getFileIcon(fileType) {
    if (fileType.startsWith('image/')) return '🖼️';
    if (fileType.startsWith('video/')) return '🎥';
    if (fileType.startsWith('audio/')) return '🎵';
    if (fileType.includes('pdf')) return '📄';
    if (fileType.includes('text')) return '📝';
    if (fileType.includes('zip') || fileType.includes('rar')) return '📦';
    return '📄';
  }
  function sortItems(items, by, order) {
    return [...items].sort((a, b) => {
      let aVal, bVal;
      switch (by) {
        case 'name':
          aVal = (a.filename || a.name || '').toLowerCase();
          bVal = (b.filename || b.name || '').toLowerCase();
          break;
        case 'size':
          aVal = a.size || 0;
          bVal = b.size || 0;
          break;
        case 'date':
          aVal = new Date(a.upload_date || a.created_date);
          bVal = new Date(b.upload_date || b.created_date);
          break;
        default:
          return 0;
      }
      if (order === 'asc') return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      else return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
    });
  }
  let isDropping = false;
  function handleDragEnter(e) {
    e.preventDefault();
    isDropping = true;
  }
  function handleDragLeave(e) {
    e.preventDefault();
    isDropping = false;
  }
  async function handleDrop(e) {
    e.preventDefault();
    isDropping = false;
    await handleFileUpload(e);
  }
  function toggleFileSelection(fileId) {
    selectedFiles.update((set) => {
      const n = new Set(set);
      if (n.has(fileId)) n.delete(fileId);
      else n.add(fileId);
      return n;
    });
    updateBulkActionsVisibility();
  }
  function toggleFolderSelection(folderId) {
    selectedFolders.update((set) => {
      const n = new Set(set);
      if (n.has(folderId)) n.delete(folderId);
      else n.add(folderId);
      return n;
    });
    updateBulkActionsVisibility();
  }
  function toggleSelectAll() {
    selectAll.update((v) => !v);
    if ($selectAll) {
      selectedFiles.set(new Set($files.map((f) => f._id)));
      selectedFolders.set(new Set($folders.map((f) => f._id)));
    } else {
      selectedFiles.set(new Set());
      selectedFolders.set(new Set());
    }
    updateBulkActionsVisibility();
  }
  function updateBulkActionsVisibility() {
    const hasSelection = $selectedFiles.size > 0 || $selectedFolders.size > 0;
    showBulkActions.set(hasSelection);
  }
  function clearSelections() {
    selectedFiles.set(new Set());
    selectedFolders.set(new Set());
    selectAll.set(false);
    showBulkActions.set(false);
  }
  async function deleteSelectedItems() {
    if (
      !confirm(
        `¿Estás seguro de que quieres eliminar ${$selectedFiles.size + $selectedFolders.size} elemento(s)?`
      )
    )
      return;
    try {
      for (const fileId of $selectedFiles) {
        const r = await authFetch(`${API_URL}/files/delete/${fileId}`, { method: 'DELETE' });
        if (!r.ok) throw new Error(`Error al eliminar archivo ${fileId}`);
      }
      for (const folderId of $selectedFolders) {
        const r = await authFetch(`${API_URL}/folders/${folderId}`, { method: 'DELETE' });
        if (!r.ok) throw new Error(`Error al eliminar carpeta ${folderId}`);
      }
      successMessage.set('Elementos eliminados correctamente');
      clearSelections();
      await loadFolderContent($currentFolder);
    } catch (e) {
      errorMessage.set(e.message);
    }
  }
  async function moveSelectedItems() {
    if ($selectedFiles.size === 0 && $selectedFolders.size === 0) return;
    await openFolderSelector();
  }
  async function copySelectedItems() {
    if ($selectedFiles.size === 0 && $selectedFolders.size === 0) return;
    await openFolderSelector('copy');
  }
  function canPreview(fileType) {
    const previewable = [
      'image/jpeg',
      'image/jpg',
      'image/png',
      'image/gif',
      'image/webp',
      'image/svg+xml',
      'text/plain',
      'text/html',
      'text/css',
      'text/javascript',
      'application/javascript',
      'application/json',
      'text/markdown',
      'text/csv',
      'application/pdf',
    ];
    return previewable.includes(fileType.toLowerCase());
  }
  async function openPreview(file) {
    previewFile.set(file);
    previewContent.set('');
    previewError.set('');
    showPreview.set(true);
    try {
      const fileType = file.file_type.toLowerCase();
      if (fileType.startsWith('image/')) {
        try {
          const resp = await authFetch(`${API_URL}/files/download/${file._id}?inline=true`);
          if (!resp.ok) throw new Error('No se pudo cargar la imagen');
          const blob = await resp.blob();
          const imageUrl = URL.createObjectURL(blob);
          previewContent.set(imageUrl);
          return;
        } catch (e) {
          previewError.set('Error al cargar la vista previa de la imagen');
          return;
        }
      }
      if (fileType === 'application/pdf') {
        try {
          const resp = await authFetch(`${API_URL}/files/download/${file._id}?inline=true`);
          if (!resp.ok) throw new Error('No se pudo cargar el PDF');
          const blob = await resp.blob();
          const pdfUrl = URL.createObjectURL(blob);
          previewContent.set(pdfUrl);
          return;
        } catch (e) {
          previewError.set('Error al cargar la vista previa del PDF');
          return;
        }
      }
      if (
        fileType.startsWith('text/') ||
        fileType === 'application/json' ||
        fileType === 'application/javascript'
      ) {
        const resp = await authFetch(`${API_URL}/files/download/${file._id}`);
        if (!resp.ok) throw new Error('Error al cargar el archivo');
        const text = await resp.text();
        previewContent.set(text);
        return;
      }
    } catch (e) {
      previewError.set('Error al cargar la previsualización: ' + e.message);
    }
  }
  function closePreview() {
    const currentContent = $previewContent;
    if (currentContent && currentContent.startsWith('blob:')) URL.revokeObjectURL(currentContent);
    showPreview.set(false);
    previewFile.set(null);
    previewContent.set('');
    previewError.set('');
  }

  async function downloadFile(fileId, filename) {
    try {
      const resp = await authFetch(`${API_URL}/files/download/${fileId}`);
      if (!resp.ok) throw new Error('Error al descargar el archivo');

      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);

      // Crear enlace temporal para descargar
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);

      // Limpiar el blob URL
      URL.revokeObjectURL(url);
    } catch (error) {
      errorMessage.set('Error al descargar el archivo: ' + error.message);
      setTimeout(() => errorMessage.set(''), 3000);
    }
  }

  // Cache para miniaturas de imagen
  const thumbnailCache = new Map();

  async function loadThumbnail(fileId) {
    // Si ya está en cache, devolverla
    if (thumbnailCache.has(fileId)) {
      return thumbnailCache.get(fileId);
    }

    try {
      const resp = await authFetch(`${API_URL}/files/download/${fileId}`);
      if (!resp.ok) throw new Error('Error al cargar miniatura');

      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);

      // Guardar en cache
      thumbnailCache.set(fileId, url);
      return url;
    } catch (error) {
      console.error('Error loading thumbnail:', error);
      return null;
    }
  }

  function isImageFile(fileType) {
    return (
      fileType &&
      (fileType.startsWith('image/') ||
        ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'].includes(fileType.toLowerCase()))
    );
  }

  // Limpiar cache cuando se cambie de carpeta
  function clearThumbnailCache() {
    thumbnailCache.forEach((url) => {
      if (url && url.startsWith('blob:')) {
        URL.revokeObjectURL(url);
      }
    });
    thumbnailCache.clear();
  }

  async function loadSelectorFolderContent(folderId = 'root') {
    try {
      const response = await authFetch(`${API_URL}/folders?parent_folder_id=${folderId}`);
      if (!response.ok) throw new Error('Error al cargar contenido');
      const fs = await response.json();
      allFolders.set(fs);
      selectorCurrentFolder.set(folderId);
    } catch (e) {
      errorMessage.set('Error al cargar carpetas');
    }
  }
  async function openFolderSelector(mode = 'move') {
    selectedTargetFolder.set(null);
    selectorMode.set(mode);
    await loadSelectorFolderContent('root');
    showFolderSelector.set(true);
  }
  function closeFolderSelector() {
    showFolderSelector.set(false);
    selectedTargetFolder.set(null);
    allFolders.set([]);
  }
  function selectTargetFolder(folder) {
    selectedTargetFolder.set(folder);
  }
  function navigateToFolderInSelector(folderId) {
    loadSelectorFolderContent(folderId);
  }
  async function confirmAction() {
    const targetFolder = $selectedTargetFolder;
    const mode = $selectorMode;
    const isMove = mode === 'move';
    try {
      for (const fileId of $selectedFiles) {
        const endpoint = isMove
          ? `${API_URL}/files/${fileId}/move`
          : `${API_URL}/files/${fileId}/copy`;
        const method = isMove ? 'PATCH' : 'POST';
        const r = await authFetch(endpoint, {
          method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ folder_id: targetFolder ? targetFolder._id : null }),
        });
        if (!r.ok) throw new Error(`Error al ${isMove ? 'mover' : 'copiar'} archivo ${fileId}`);
      }
      for (const folderId of $selectedFolders) {
        const endpoint = isMove
          ? `${API_URL}/folders/${folderId}/move`
          : `${API_URL}/folders/${folderId}/copy`;
        const method = isMove ? 'PATCH' : 'POST';
        const r = await authFetch(endpoint, {
          method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ parent_folder_id: targetFolder ? targetFolder._id : null }),
        });
        if (!r.ok) throw new Error(`Error al ${isMove ? 'mover' : 'copiar'} carpeta ${folderId}`);
      }
      const targetName = targetFolder ? targetFolder.name : 'Raíz';
      const actionName = isMove ? 'movido(s)' : 'copiado(s)';
      successMessage.set(
        `${$selectedFiles.size + $selectedFolders.size} elemento(s) ${actionName} a "${targetName}" correctamente`
      );
      if (isMove) clearSelections();
      closeFolderSelector();
      await loadFolderContent($currentFolder);
    } catch (e) {
      errorMessage.set(e.message);
    }
  }
  $: sortedFiles = sortItems($files, $sortBy, $sortOrder);
  $: sortedFolders = sortItems($folders, $sortBy, $sortOrder);
  $: {
    const totalItems = $files.length + $folders.length;
    const selectedItems = $selectedFiles.size + $selectedFolders.size;
    if (totalItems > 0 && selectedItems === totalItems && !$selectAll) {
      selectAll.set(true);
    } else if (selectedItems === 0 && $selectAll) {
      selectAll.set(false);
    }
  }
  $: if ($currentFolder) {
    clearSelections();
  }
  onDestroy(() => {
    const currentContent = $previewContent;
    if (currentContent && currentContent.startsWith('blob:')) URL.revokeObjectURL(currentContent);

    // Limpiar cache de miniaturas
    clearThumbnailCache();
  });
  let debounceTimer;
  $: if ($searchTerm !== undefined && $currentFolder) {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      searchFiles();
    }, 300);
  }
</script>

{#if $showAuthScreen}
  <main
    class="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-blue-100 p-4"
  >
    <div class="bg-white w-full max-w-md rounded-2xl shadow-lg p-8 space-y-6">
      <h1 class="text-2xl font-bold text-center text-gray-800">
        {$authMode === 'login' ? 'Iniciar Sesión' : 'Crear Cuenta'}
      </h1>
      <p class="text-center text-sm text-gray-500">
        Accede a tu Drive. Usuario admin por defecto: admin / admin123
      </p>
      {#if $authError}
        <div class="bg-red-100 text-red-700 text-sm px-4 py-2 rounded">{$authError}</div>
      {/if}
      <form on:submit|preventDefault={handleAuthSubmit} class="space-y-4">
        <div>
          <label for="username" class="block text-sm font-medium text-gray-700 mb-1">Usuario</label>
          <input
            id="username"
            type="text"
            bind:value={$authUsername}
            on:keydown={handleKeyPress}
            class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="usuario"
            disabled={$authLoading}
          />
        </div>
        <div>
          <label for="password" class="block text-sm font-medium text-gray-700 mb-1"
            >Contraseña</label
          >
          <input
            id="password"
            type="password"
            bind:value={$authPassword}
            on:keydown={handleKeyPress}
            class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="••••••••"
            disabled={$authLoading}
          />
        </div>
        <button
          type="submit"
          class="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 rounded-lg transition-colors disabled:opacity-50"
          disabled={$authLoading}
        >
          {#if $authLoading}Procesando...{:else}{$authMode === 'login'
              ? 'Entrar'
              : 'Registrarme'}{/if}
        </button>
      </form>
      <div class="text-center text-sm text-gray-600">
        {#if $authMode === 'login'}
          ¿No tienes cuenta? <button
            class="text-blue-600 hover:underline"
            on:click={() => {
              authMode.set('register');
              authError.set('');
            }}>Registrarme</button
          >
        {:else}
          ¿Ya tienes cuenta? <button
            class="text-blue-600 hover:underline"
            on:click={() => {
              authMode.set('login');
              authError.set('');
            }}>Entrar</button
          >
        {/if}
      </div>
    </div>
  </main>
{:else}
  <!-- EXISTING APP CONTENT WRAPPED -->
  <main class="bg-gray-50 min-h-screen">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Header -->
      <header class="mb-8 flex items-center justify-between">
        <div>
          <h1 class="text-4xl font-bold text-gray-900">Mi Drive</h1>
          <p class="text-gray-600 mt-1">Gestiona tus archivos y carpetas de forma sencilla</p>
        </div>
        <div class="flex items-center space-x-4">
          <button class="text-sm text-gray-600 hover:text-red-600" on:click={logout}
            >🔐 Cerrar sesión</button
          >
          <div class="flex border rounded-lg overflow-hidden">
            <button
              class="px-3 py-2 text-sm {$viewMode === 'list'
                ? 'bg-blue-500 text-white'
                : 'bg-white text-gray-700'}"
              on:click={() => viewMode.set('list')}>📋 Lista</button
            >
            <button
              class="px-3 py-2 text-sm {$viewMode === 'grid'
                ? 'bg-blue-500 text-white'
                : 'bg-white text-gray-700'}"
              on:click={() => viewMode.set('grid')}>⊞ Cuadrícula</button
            >
          </div>
        </div>
      </header>

      <!-- Navigation Breadcrumb -->
      <nav class="mb-6">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2 text-sm text-gray-600">
            <button
              class="hover:text-blue-600 hover:underline"
              on:click={() => navigateToFolder('root')}
            >
              🏠 Inicio
            </button>
            {#if $folderPath !== '/'}
              <span>/</span>
              <span class="text-gray-900 font-medium">{$folderPath}</span>
            {/if}
          </div>

          <!-- Back Navigation Button -->
          {#if $currentFolder !== 'root' && $currentFolderInfo}
            <button
              class="flex items-center px-3 py-2 text-sm text-gray-600 hover:text-blue-600 hover:bg-gray-100 rounded-lg transition-colors"
              on:click={navigateBack}
              title="Ir a la carpeta anterior"
            >
              ⬆️ Subir nivel
            </button>
          {/if}
        </div>
      </nav>

      <!-- Toolbar -->
      <div class="bg-white rounded-lg shadow-sm p-4 mb-6">
        <div
          class="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0"
        >
          <!-- Search and Create Controls -->
          <div class="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-4 items-center">
            <!-- Search -->
            <div class="relative">
              <input
                type="text"
                placeholder="Buscar archivos..."
                bind:value={$searchTerm}
                class="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <div class="absolute left-3 top-2.5 text-gray-400">🔍</div>
            </div>

            <!-- Create Folder Button -->
            <button
              on:click={() => showCreateFolder.set(true)}
              class="flex items-center px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
            >
              📁 Nueva Carpeta
            </button>

            <!-- Información de Selección Múltiple -->
            {#if $showBulkActions}
              <div
                class="flex items-center space-x-3 bg-blue-50 px-3 py-2 rounded-lg border border-blue-200"
              >
                <span class="text-sm font-medium text-blue-800">
                  {$selectedFiles.size + $selectedFolders.size} seleccionados
                </span>
                <button
                  on:click={clearSelections}
                  class="text-xs text-blue-600 hover:text-blue-800 underline"
                >
                  Desmarcar
                </button>

                <!-- Botones de acción compactos -->
                <div class="flex items-center space-x-1">
                  <button
                    on:click={deleteSelectedItems}
                    class="p-1.5 bg-red-600 text-white text-xs rounded hover:bg-red-700 transition-colors"
                    title="Eliminar seleccionados"
                  >
                    🗑️ Eliminar
                  </button>

                  <button
                    on:click={moveSelectedItems}
                    class="p-1.5 bg-green-600 text-white text-xs rounded hover:bg-green-700 transition-colors"
                    title="Mover seleccionados"
                  >
                    📁 Mover
                  </button>

                  <button
                    on:click={copySelectedItems}
                    class="p-1.5 bg-purple-600 text-white text-xs rounded hover:bg-purple-700 transition-colors"
                    title="Copiar seleccionados"
                  >
                    📋 Copiar
                  </button>
                </div>
              </div>
            {/if}
          </div>

          <!-- Sort Controls -->
          <div class="flex items-center space-x-2">
            <label class="text-sm text-gray-600">Ordenar por:</label>
            <select bind:value={$sortBy} class="px-3 py-1 border border-gray-300 rounded text-sm">
              <option value="name">Nombre</option>
              <option value="date">Fecha</option>
              <option value="size">Tamaño</option>
            </select>
            <button
              on:click={() => sortOrder.set($sortOrder === 'asc' ? 'desc' : 'asc')}
              class="p-1 text-gray-600 hover:text-gray-900"
              title="Cambiar orden"
            >
              {$sortOrder === 'asc' ? '⬆️' : '⬇️'}
            </button>
          </div>
        </div>
      </div>

      <!-- File Upload Area -->
      <div
        class="bg-white p-6 rounded-lg shadow-sm mb-6 border-2 border-dashed transition-all duration-300 {isDropping
          ? 'border-blue-500 bg-blue-50'
          : 'border-gray-300'}"
        on:dragenter={handleDragEnter}
        on:dragleave={handleDragLeave}
        on:dragover|preventDefault
        on:drop={handleDrop}
      >
        <div class="text-center">
          <div class="text-4xl mb-4">📤</div>
          <h3 class="text-lg font-medium text-gray-900 mb-2">Subir archivos</h3>
          <p class="text-gray-600 mb-4">Arrastra archivos aquí o selecciona desde tu computadora</p>
          <label
            for="file-upload"
            class="inline-flex items-center px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 cursor-pointer transition-colors"
          >
            📎 Seleccionar Archivos
          </label>
          <input
            id="file-upload"
            type="file"
            class="hidden"
            on:change={handleFileUpload}
            multiple
          />
        </div>
      </div>

      <!-- Create Folder Modal -->
      {#if $showCreateFolder}
        <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div class="bg-white p-6 rounded-lg shadow-xl max-w-md w-full mx-4">
            <h3 class="text-lg font-medium mb-4">Crear Nueva Carpeta</h3>
            <input
              type="text"
              placeholder="Nombre de la carpeta"
              bind:value={$newFolderName}
              class="w-full px-3 py-2 border border-gray-300 rounded-lg mb-4"
              on:keydown={(e) => e.key === 'Enter' && createFolder()}
            />
            <div class="flex justify-end space-x-3">
              <button
                on:click={() => showCreateFolder.set(false)}
                class="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                Cancelar
              </button>
              <button
                on:click={createFolder}
                class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
              >
                Crear
              </button>
            </div>
          </div>
        </div>
      {/if}

      <!-- Content Display -->
      <div class="bg-white rounded-lg shadow-sm overflow-hidden">
        {#if $viewMode === 'list'}
          <!-- List View -->
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th
                    class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-16"
                  >
                    <input
                      type="checkbox"
                      bind:checked={$selectAll}
                      on:change={toggleSelectAll}
                      class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      title="Seleccionar todo"
                    />
                  </th>
                  <th
                    class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >Nombre</th
                  >
                  <th
                    class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >Tamaño</th
                  >
                  <th
                    class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >Modificado</th
                  >
                  <th
                    class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >Acciones</th
                  >
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                <!-- Folders -->
                {#each sortedFolders as folder (folder._id)}
                  <tr class="hover:bg-gray-50">
                    <td class="px-6 py-4 whitespace-nowrap">
                      <input
                        type="checkbox"
                        checked={$selectedFolders.has(folder._id)}
                        on:change={() => toggleFolderSelection(folder._id)}
                        class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        on:click={(e) => e.stopPropagation()}
                      />
                    </td>
                    <td
                      class="px-6 py-4 whitespace-nowrap cursor-pointer"
                      on:click={() => navigateToFolder(folder._id)}
                    >
                      <div class="flex items-center">
                        <span class="text-2xl mr-3">📁</span>
                        <span class="text-sm font-medium text-gray-900">{folder.name}</span>
                      </div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">—</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500"
                      >{formatDate(folder.created_date)}</td
                    >
                    <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        on:click={() => deleteFolder(folder._id)}
                        class="text-red-600 hover:text-red-900 ml-4"
                      >
                        🗑️ Eliminar
                      </button>
                    </td>
                  </tr>
                {/each}

                <!-- Files -->
                {#each sortedFiles as file (file._id)}
                  <tr class="hover:bg-gray-50">
                    <td class="px-6 py-4 whitespace-nowrap">
                      <input
                        type="checkbox"
                        checked={$selectedFiles.has(file._id)}
                        on:change={() => toggleFileSelection(file._id)}
                        class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        on:click={(e) => e.stopPropagation()}
                      />
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                      {#if $editingFileId === file._id}
                        <div class="flex items-center">
                          <span class="text-xl mr-3">{getFileIcon(file.file_type)}</span>
                          <input
                            type="text"
                            bind:value={$newFileName}
                            class="border rounded px-2 py-1 text-sm mr-2"
                            on:keydown={(e) => {
                              if (e.key === 'Enter') saveFileName(file._id, true);
                              if (e.key === 'Escape') cancelEditing();
                            }}
                            placeholder="Nombre del archivo"
                            autofocus
                          />
                          <button
                            on:click={() => saveFileName(file._id, true)}
                            class="text-xs bg-green-600 text-white px-2 py-1 rounded mr-1 hover:bg-green-700"
                          >
                            ✓ Guardar
                          </button>
                          <button
                            on:click={cancelEditing}
                            class="text-xs bg-gray-500 text-white px-2 py-1 rounded hover:bg-gray-600"
                          >
                            ✕ Cancelar
                          </button>
                        </div>
                      {:else}
                        <div class="flex items-center">
                          <span class="text-xl mr-3">{getFileIcon(file.file_type)}</span>
                          <span class="text-sm font-medium text-gray-900">{file.filename}</span>
                        </div>
                      {/if}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500"
                      >{formatBytes(file.size)}</td
                    >
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500"
                      >{formatDate(file.upload_date)}</td
                    >
                    <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      {#if canPreview(file.file_type)}
                        <button
                          on:click={() => openPreview(file)}
                          class="text-blue-600 hover:text-blue-900 mr-3">👁️ Preview</button
                        >
                      {/if}
                      <button
                        on:click={() => startEditingFile(file)}
                        class="text-indigo-600 hover:text-indigo-900 mr-3">✏️ Editar</button
                      >
                      <button
                        on:click={() => downloadFile(file._id, file.filename)}
                        class="text-green-600 hover:text-green-900 mr-3">⬇️ Descargar</button
                      >
                      <button
                        on:click={() => handleDeleteFile(file._id)}
                        class="text-red-600 hover:text-red-900">🗑️ Eliminar</button
                      >
                    </td>
                  </tr>
                {/each}

                {#if sortedFolders.length === 0 && sortedFiles.length === 0}
                  <tr>
                    <td colspan="5" class="text-center py-12 text-gray-500">
                      <div class="text-4xl mb-4">📂</div>
                      {#if $searchTerm}
                        No se encontraron resultados para "{$searchTerm}"
                      {:else}
                        Esta carpeta está vacía. ¡Sube tu primer archivo!
                      {/if}
                    </td>
                  </tr>
                {/if}
              </tbody>
            </table>
          </div>
        {:else}
          <!-- Grid View -->
          <div class="p-6">
            <!-- Grid Controls -->
            <div class="flex items-center justify-between mb-4">
              <div class="flex items-center space-x-3">
                <input
                  type="checkbox"
                  bind:checked={$selectAll}
                  on:change={toggleSelectAll}
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <label class="text-sm text-gray-600">Seleccionar todo</label>
              </div>

              {#if $showBulkActions}
                <div class="text-sm text-gray-600">
                  {$selectedFiles.size + $selectedFolders.size} elemento(s) seleccionado(s)
                </div>
              {/if}
            </div>

            <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
              <!-- Folders -->
              {#each sortedFolders as folder (folder._id)}
                <div class="relative group">
                  <!-- Checkbox -->
                  <input
                    type="checkbox"
                    checked={$selectedFolders.has(folder._id)}
                    on:change={() => toggleFolderSelection(folder._id)}
                    class="absolute top-2 left-2 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded z-10"
                    on:click={(e) => e.stopPropagation()}
                  />
                  <div
                    class="bg-gray-50 rounded-lg p-4 hover:bg-gray-100 cursor-pointer transition-colors"
                    on:click={() => navigateToFolder(folder._id)}
                  >
                    <div class="text-center">
                      <div class="text-4xl mb-2">📁</div>
                      <p class="text-sm font-medium text-gray-900 truncate">{folder.name}</p>
                      <p class="text-xs text-gray-500 mt-1">{formatDate(folder.created_date)}</p>
                    </div>
                  </div>
                  <button
                    on:click={() => deleteFolder(folder._id)}
                    class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs transition-opacity"
                  >
                    ✕
                  </button>
                </div>
              {/each}

              <!-- Files -->
              {#each sortedFiles as file (file._id)}
                <div class="relative group">
                  <!-- Checkbox -->
                  <input
                    type="checkbox"
                    checked={$selectedFiles.has(file._id)}
                    on:change={() => toggleFileSelection(file._id)}
                    class="absolute top-2 left-2 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded z-10"
                    on:click={(e) => e.stopPropagation()}
                  />
                  <div
                    class="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                  >
                    <div class="text-center">
                      {#if isImageFile(file.file_type)}
                        <div
                          class="w-16 h-16 mx-auto mb-2 bg-gray-100 rounded-lg overflow-hidden flex items-center justify-center"
                        >
                          {#await loadThumbnail(file._id)}
                            <div class="text-2xl text-gray-400">🖼️</div>
                          {:then thumbnailUrl}
                            {#if thumbnailUrl}
                              <img
                                src={thumbnailUrl}
                                alt={file.filename}
                                class="w-full h-full object-cover"
                                loading="lazy"
                              />
                            {:else}
                              <div class="text-2xl text-gray-400">🖼️</div>
                            {/if}
                          {:catch}
                            <div class="text-2xl text-gray-400">🖼️</div>
                          {/await}
                        </div>
                      {:else}
                        <div class="text-4xl mb-2">{getFileIcon(file.file_type)}</div>
                      {/if}
                      {#if $editingFileId === file._id}
                        <input
                          type="text"
                          bind:value={$newFileName}
                          class="w-full text-xs border rounded px-1 py-0.5 mb-1"
                          on:keydown={(e) => e.key === 'Enter' && saveFileName(file._id)}
                          on:blur={() => saveFileName(file._id)}
                        />
                      {:else}
                        <p class="text-sm font-medium text-gray-900 truncate mb-1">
                          {file.filename}
                        </p>
                      {/if}
                      <p class="text-xs text-gray-500">{formatBytes(file.size)}</p>
                      <p class="text-xs text-gray-400">{formatDate(file.upload_date)}</p>
                    </div>

                    <!-- File Actions -->
                    <div class="mt-3 flex justify-center space-x-2">
                      {#if canPreview(file.file_type)}
                        <button
                          on:click={() => openPreview(file)}
                          class="text-xs text-blue-600 hover:text-blue-900"
                          title="Preview">👁️</button
                        >
                      {/if}
                      <button
                        on:click={() => startEditingFile(file)}
                        class="text-xs text-indigo-600 hover:text-indigo-900">✏️</button
                      >
                      <button
                        on:click={() => downloadFile(file._id, file.filename)}
                        class="text-xs text-green-600 hover:text-green-900">⬇️</button
                      >
                      <button
                        on:click={() => handleDeleteFile(file._id)}
                        class="text-xs text-red-600 hover:text-red-900">🗑️</button
                      >
                    </div>
                  </div>
                </div>
              {/each}

              {#if sortedFolders.length === 0 && sortedFiles.length === 0}
                <div class="col-span-full text-center py-12 text-gray-500">
                  <div class="text-6xl mb-4">📂</div>
                  {#if $searchTerm}
                    <p>No se encontraron resultados para "{$searchTerm}"</p>
                  {:else}
                    <p>Esta carpeta está vacía. ¡Sube tu primer archivo!</p>
                  {/if}
                </div>
              {/if}
            </div>
          </div>
        {/if}
      </div>

      <!-- Statistics Footer -->
      <div class="mt-8 text-center text-sm text-gray-500">
        {sortedFolders.length} carpeta{sortedFolders.length !== 1 ? 's' : ''},
        {sortedFiles.length} archivo{sortedFiles.length !== 1 ? 's' : ''}
        {#if $searchTerm}
          · Resultados de búsqueda para "{$searchTerm}"
        {/if}
      </div>
    </div>

    <!-- Notification Popups (Fixed Bottom Right) -->
    <div class="fixed bottom-4 right-4 z-50 flex flex-col space-y-3">
      <!-- Loading/Upload Progress Popup -->
      {#if $isLoading}
        <div class="loading-popup">
          {#if $uploadProgress}
            <!-- Upload Progress with Progress Bar -->
            <div class="bg-blue-500 text-white px-5 py-4 rounded-lg shadow-lg upload-popup">
              <div class="flex items-center space-x-3 mb-3">
                <div class="text-xl">📤</div>
                <span class="font-semibold">Subiendo archivo</span>
              </div>

              <!-- File Info -->
              <div class="text-sm opacity-90 mb-3">
                <div class="truncate font-medium mb-1">{$uploadProgress.fileName}</div>
                <div class="text-xs opacity-75">
                  Archivo {$uploadProgress.currentFile} de {$uploadProgress.totalFiles}
                </div>
              </div>

              <!-- Progress Bar Container -->
              <div class="upload-progress-container mb-3">
                <div class="w-full bg-blue-700 rounded-full h-2.5 overflow-hidden">
                  <div
                    class="upload-progress-bar h-2.5 rounded-full progress-bar"
                    style="width: {$uploadProgress.progress}%"
                  ></div>
                </div>
              </div>

              <!-- Progress Percentage -->
              <div class="flex justify-between items-center text-sm">
                <span class="opacity-75">Progreso</span>
                <span class="font-bold text-blue-100">{$uploadProgress.progress}%</span>
              </div>
            </div>
          {:else}
            <!-- Generic Loading -->
            <div
              class="bg-blue-500 text-white px-4 py-3 rounded-lg shadow-lg flex items-center space-x-3"
            >
              <div
                class="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"
              ></div>
              <span class="font-medium">Cargando...</span>
            </div>
          {/if}
        </div>
      {/if}

      <!-- Success Popup -->
      {#if $successMessage}
        <div class="success-popup">
          <div
            class="bg-green-500 text-white px-4 py-3 rounded-lg shadow-lg flex items-center space-x-3"
          >
            <div class="text-lg">✅</div>
            <span class="font-medium">{$successMessage}</span>
          </div>
        </div>
      {/if}

      <!-- Error Popup -->
      {#if $errorMessage}
        <div class="error-popup">
          <div
            class="bg-red-500 text-white px-4 py-3 rounded-lg shadow-lg flex items-center space-x-3"
          >
            <div class="text-lg">❌</div>
            <span class="font-medium">{$errorMessage}</span>
          </div>
        </div>
      {/if}
    </div>

    <!-- Modal de Preview -->
    {#if $showPreview}
      <div
        class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 preview-modal"
        on:click={closePreview}
      >
        <div
          class="bg-white rounded-lg shadow-xl max-w-4xl max-h-[90vh] w-full mx-4 overflow-hidden preview-modal-content"
          on:click={(e) => e.stopPropagation()}
        >
          <!-- Header del modal -->
          <div class="flex items-center justify-between p-4 border-b border-gray-200">
            <div class="flex items-center space-x-3">
              <span class="text-2xl"
                >{$previewFile ? getFileIcon($previewFile.file_type) : '📄'}</span
              >
              <div>
                <h3 class="text-lg font-semibold text-gray-900">
                  {$previewFile?.filename || 'Preview'}
                </h3>
                <p class="text-sm text-gray-500">
                  {$previewFile ? formatBytes($previewFile.size) : ''}
                </p>
              </div>
            </div>
            <button
              on:click={closePreview}
              class="text-gray-400 hover:text-gray-600 text-2xl font-bold"
            >
              ✕
            </button>
          </div>

          <!-- Contenido del preview -->
          <div class="p-4 overflow-auto max-h-[calc(90vh-120px)]">
            {#if $previewError}
              <div class="text-center py-8">
                <div class="text-4xl mb-4">⚠️</div>
                <p class="text-red-600">{$previewError}</p>
              </div>
            {:else if $previewFile}
              {#if $previewFile.file_type.startsWith('image/')}
                <!-- Preview de imagen -->
                <div class="text-center">
                  <img
                    src={$previewContent}
                    alt={$previewFile.filename}
                    class="max-w-full max-h-[70vh] object-contain mx-auto rounded"
                    on:error={() => previewError.set('Error al cargar la imagen')}
                  />
                </div>
              {:else if $previewFile.file_type === 'application/pdf'}
                <!-- Preview de PDF -->
                <div class="w-full h-[70vh]">
                  <iframe
                    src={$previewContent}
                    class="w-full h-full border-0 rounded"
                    title="PDF Preview"
                  ></iframe>
                </div>
              {:else if $previewFile.file_type.startsWith('text/') || $previewFile.file_type === 'application/json' || $previewFile.file_type === 'application/javascript'}
                <!-- Preview de texto -->
                <div class="bg-gray-50 rounded-lg p-4">
                  <pre
                    class="text-sm text-gray-800 whitespace-pre-wrap overflow-auto max-h-[60vh] font-mono">{$previewContent}</pre>
                </div>
              {:else}
                <!-- Tipo no soportado -->
                <div class="text-center py-8">
                  <div class="text-4xl mb-4">📄</div>
                  <p class="text-gray-600">Este tipo de archivo no se puede previsualizar</p>
                  <button
                    on:click={() => downloadFile($previewFile._id, $previewFile.filename)}
                    class="inline-block mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    ⬇️ Descargar archivo
                  </button>
                </div>
              {/if}
            {/if}
          </div>

          <!-- Footer del modal -->
          <div class="flex items-center justify-between p-4 border-t border-gray-200 bg-gray-50">
            <div class="text-sm text-gray-600">
              {#if $previewFile}
                Tipo: {$previewFile.file_type} • Subido: {formatDate($previewFile.upload_date)}
              {/if}
            </div>
            <div class="flex space-x-2">
              <button
                on:click={() => downloadFile($previewFile?._id, $previewFile?.filename)}
                class="px-3 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition-colors"
              >
                ⬇️ Descargar
              </button>
              <button
                on:click={closePreview}
                class="px-3 py-1.5 bg-gray-600 text-white text-sm rounded hover:bg-gray-700 transition-colors"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      </div>
    {/if}

    <!-- Modal Selector de Carpetas -->
    {#if $showFolderSelector}
      <div
        class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
        on:click={closeFolderSelector}
      >
        <div
          class="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden"
          on:click={(e) => e.stopPropagation()}
        >
          <!-- Header del modal -->
          <div class="flex items-center justify-between p-4 border-b border-gray-200">
            <div class="flex items-center space-x-3">
              <span class="text-2xl">{$selectorMode === 'move' ? '📁' : '📋'}</span>
              <div>
                <h3 class="text-lg font-semibold text-gray-900">
                  {$selectorMode === 'move'
                    ? 'Seleccionar Carpeta de Destino'
                    : 'Seleccionar Carpeta para Copiar'}
                </h3>
                <p class="text-sm text-gray-500">
                  {$selectorMode === 'move'
                    ? 'Elige dónde mover los elementos seleccionados'
                    : 'Elige dónde copiar los elementos seleccionados'}
                </p>
              </div>
            </div>
            <button
              on:click={closeFolderSelector}
              class="text-gray-400 hover:text-gray-600 text-2xl font-bold"
            >
              ✕
            </button>
          </div>

          <!-- Navegación del selector -->
          <div class="p-4 bg-gray-50 border-b border-gray-200">
            <div class="flex items-center space-x-2">
              <button
                on:click={() => navigateToFolderInSelector('root')}
                class="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors flex items-center space-x-1"
              >
                <span>🏠</span>
                <span>Raíz</span>
              </button>
              {#if $selectorCurrentFolder !== 'root'}
                <span class="text-gray-400">→</span>
                <span class="text-sm text-gray-600">Carpeta actual</span>
              {/if}
            </div>
          </div>

          <!-- Lista de carpetas -->
          <div class="p-4 overflow-y-auto max-h-[50vh]">
            <!-- Opción de raíz -->
            <div
              class="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-100 cursor-pointer border-2 transition-colors {$selectedTargetFolder ===
              null
                ? 'border-blue-500 bg-blue-50'
                : 'border-transparent'}"
              on:click={() => selectTargetFolder(null)}
            >
              <span class="text-2xl">🏠</span>
              <div class="flex-1">
                <p class="font-medium text-gray-900">Carpeta Raíz</p>
                <p class="text-sm text-gray-500">
                  {$selectorMode === 'move'
                    ? 'Mover a la carpeta principal'
                    : 'Copiar a la carpeta principal'}
                </p>
              </div>
              {#if $selectedTargetFolder === null}
                <span class="text-blue-600 text-xl">✓</span>
              {/if}
            </div>

            <!-- Carpetas disponibles -->
            {#each $allFolders as folder}
              <div
                class="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-100 cursor-pointer border-2 transition-colors {$selectedTargetFolder?._id ===
                folder._id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-transparent'}"
                on:click={() => selectTargetFolder(folder)}
              >
                <span class="text-2xl">📁</span>
                <div class="flex-1">
                  <p class="font-medium text-gray-900">{folder.name}</p>
                  <p class="text-sm text-gray-500">Creada: {formatDate(folder.created_date)}</p>
                </div>
                <div class="flex items-center space-x-2">
                  {#if $selectedTargetFolder?._id === folder._id}
                    <span class="text-blue-600 text-xl">✓</span>
                  {/if}
                  <button
                    on:click={(e) => {
                      e.stopPropagation();
                      navigateToFolderInSelector(folder._id);
                    }}
                    class="px-2 py-1 bg-gray-200 text-gray-700 text-sm rounded hover:bg-gray-300 transition-colors"
                    title="Explorar carpeta"
                  >
                    ➡️
                  </button>
                </div>
              </div>
            {/each}

            {#if $allFolders.length === 0}
              <div class="text-center py-8 text-gray-500">
                <div class="text-4xl mb-2">📂</div>
                <p>No hay carpetas disponibles en esta ubicación</p>
              </div>
            {/if}
          </div>

          <!-- Footer del modal -->
          <div class="flex items-center justify-between p-4 border-t border-gray-200 bg-gray-50">
            <div class="text-sm text-gray-600">
              {#if $selectedTargetFolder}
                Seleccionado: <strong>{$selectedTargetFolder.name}</strong>
              {:else if $selectedTargetFolder === null}
                Seleccionado: <strong>Carpeta Raíz</strong>
              {:else}
                Selecciona una carpeta de destino
              {/if}
            </div>
            <div class="flex space-x-2">
              <button
                on:click={closeFolderSelector}
                class="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
              >
                Cancelar
              </button>
              <button
                on:click={confirmAction}
                disabled={$selectedTargetFolder === undefined}
                class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {$selectorMode === 'move' ? 'Mover' : 'Copiar'} aquí ({$selectedFiles.size +
                  $selectedFolders.size} elementos)
              </button>
            </div>
          </div>
        </div>
      </div>
    {/if}
  </main>
{/if}

<!-- El resto del marcado original permanece abajo -->
<style>
  /* Custom animations */
  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes slideInFromRight {
    from {
      opacity: 0;
      transform: translateX(100%);
    }
    to {
      opacity: 1;
      transform: translateX(0);
    }
  }

  @keyframes slideOutToRight {
    from {
      opacity: 1;
      transform: translateX(0);
    }
    to {
      opacity: 0;
      transform: translateX(100%);
    }
  }

  @keyframes progressFill {
    from {
      width: 0%;
    }
    to {
      width: var(--progress-width, 0%);
    }
  }

  .fade-in {
    animation: fadeIn 0.3s ease-out;
  }

  .loading-popup {
    animation: slideInFromRight 0.3s ease-out;
  }

  .success-popup {
    animation: slideInFromRight 0.3s ease-out;
  }

  .error-popup {
    animation: slideInFromRight 0.3s ease-out;
  }

  /* Progress bar styles */
  .progress-bar {
    transition: width 0.3s ease-out;
    animation: progressFill 0.5s ease-out;
  }

  .upload-popup {
    animation: slideInFromRight 0.3s ease-out;
    min-width: 320px;
  }

  /* Smooth transition for notification popups */
  .loading-popup div,
  .success-popup div,
  .error-popup div {
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: all 0.3s ease;
  }

  /* Hover effects for popups */
  .success-popup div:hover,
  .error-popup div:hover {
    transform: translateX(-5px);
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
  }

  /* Upload progress specific styles */
  .upload-progress-container {
    position: relative;
    overflow: hidden;
  }

  .upload-progress-bar {
    background: linear-gradient(
      90deg,
      rgba(255, 255, 255, 0.9) 0%,
      rgba(255, 255, 255, 1) 50%,
      rgba(255, 255, 255, 0.9) 100%
    );
    box-shadow: inset 0 1px 2px rgba(255, 255, 255, 0.3);
    position: relative;
  }

  .upload-progress-bar::after {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
    animation: shimmer 2s infinite;
  }

  @keyframes shimmer {
    0% {
      left: -100%;
    }
    100% {
      left: 100%;
    }
  }

  /* Estilos para el modal de preview */
  .preview-modal {
    backdrop-filter: blur(4px);
  }

  .preview-modal-content {
    animation: modalSlideIn 0.3s ease-out;
  }

  @keyframes modalSlideIn {
    from {
      opacity: 0;
      transform: scale(0.9) translateY(-20px);
    }
    to {
      opacity: 1;
      transform: scale(1) translateY(0);
    }
  }
</style>
