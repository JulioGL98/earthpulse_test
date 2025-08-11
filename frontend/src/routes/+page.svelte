<script>
  import { onMount } from 'svelte';
  import { writable } from 'svelte/store';

  // --- Estado de la Aplicación ---
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

  const API_URL = 'http://localhost:8000';

  // --- Funciones de la API ---

  /**
   * Carga el contenido de una carpeta (archivos y subcarpetas)
   */
  async function loadFolderContent(folderId = 'root') {
    isLoading.set(true);
    errorMessage.set('');
    
    try {
      const response = await fetch(`${API_URL}/folders/${folderId}/content`);
      if (!response.ok) {
        throw new Error('Error al cargar el contenido de la carpeta.');
      }
      
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
    if (!$searchTerm.trim()) {
      await loadFolderContent($currentFolder || 'root');
      return;
    }

    isLoading.set(true);
    try {
      const params = new URLSearchParams({
        search: $searchTerm,
        ...(($currentFolder && $currentFolder !== 'root') && { folder_id: $currentFolder })
      });
      
      const response = await fetch(`${API_URL}/files?${params}`);
      if (!response.ok) {
        throw new Error('Error en la búsqueda.');
      }
      
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
      folderHistory.update(history => [...history, {id: $currentFolder, info: $currentFolderInfo}]);
    }
    
    await loadFolderContent(folderId);
    
    // Actualizar la ruta de navegación y información de la carpeta actual
    if (folderId === 'root' || !folderId) {
      folderPath.set('/');
      currentFolderInfo.set(null);
    } else {
      try {
        const response = await fetch(`${API_URL}/folders/${folderId}`);
        if (response.ok) {
          const folder = await response.json();
          folderPath.set(folder.path);
          currentFolderInfo.set(folder);
        }
      } catch (error) {
        console.warn('No se pudo actualizar la ruta:', error);
      }
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
        parent_folder_id: $currentFolder === 'root' || !$currentFolder ? null : $currentFolder
      };

      const response = await fetch(`${API_URL}/folders`, {
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
    if (!confirm('¿Estás seguro de que quieres eliminar esta carpeta y todo su contenido?')) {
      return;
    }

    try {
      const response = await fetch(`${API_URL}/folders/${folderId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Error al eliminar la carpeta.');
      }

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
      if (folderId && folderId !== 'root') {
        formData.append('folder_id', folderId);
      }

      // Configurar el seguimiento de progreso
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const progress = Math.round((e.loaded / e.total) * 100);
          uploadProgress.update(current => ({
            ...current,
            progress: Math.min(progress, 100) // Asegurar que no pase de 100%
          }));
        }
      });

      // Cuando la subida se completa (pero puede estar procesándose)
      xhr.upload.addEventListener('load', () => {
        uploadProgress.update(current => ({
          ...current,
          progress: 100
        }));
      });

      // Configurar manejadores de eventos para la respuesta
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const response = JSON.parse(xhr.responseText);
            resolve(response);
          } catch (error) {
            reject(new Error('Error parsing server response'));
          }
        } else {
          try {
            const errorResponse = JSON.parse(xhr.responseText);
            reject(new Error(errorResponse.detail || `Error ${xhr.status}: ${xhr.statusText}`));
          } catch (error) {
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
      xhr.send(formData);
    });
  }

  /**
   * Maneja la subida de archivos
   */
  async function handleFileUpload(e) {
    const files = Array.from(e.target.files || e.dataTransfer?.files || []);
    if (files.length === 0) {
      return;
    }

    // Obtener el valor actual de la carpeta INMEDIATAMENTE
    const currentFolderValue = $currentFolder;
    
    isLoading.set(true);
    successMessage.set('');
    errorMessage.set('');
    
    let uploadedCount = 0;
    
    try {
      // Subir archivos uno por uno con progreso
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        
        // Inicializar el estado de progreso
        uploadProgress.set({
          fileName: file.name,
          progress: 0,
          totalFiles: files.length,
          currentFile: i + 1
        });

        // Subir archivo con seguimiento de progreso
        await uploadFileWithProgress(file, currentFolderValue);
        uploadedCount++;
        
        // Pequeña pausa entre archivos para mejor UX (excepto en el último)
        if (i < files.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 500));
        }
      }
      
      // Limpiar estado de progreso
      uploadProgress.set(null);
      
      successMessage.set(`¡${uploadedCount} archivo${uploadedCount > 1 ? 's' : ''} subido${uploadedCount > 1 ? 's' : ''} con éxito!`);
      await loadFolderContent(currentFolderValue || 'root');
    } catch (error) {
      uploadProgress.set(null);
      const failedMessage = uploadedCount > 0 
        ? `${uploadedCount} archivos subidos. Error en: ${error.message}`
        : `Error al subir archivo: ${error.message}`;
      errorMessage.set(failedMessage);
    } finally {
      // Limpiar el input file para permitir subir el mismo archivo otra vez
      const fileInput = document.getElementById('file-upload');
      if (fileInput) {
        fileInput.value = '';
      }
      
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
    if (!confirm('¿Estás seguro de que quieres eliminar este archivo?')) {
      return;
    }

    try {
      const response = await fetch(`${API_URL}/files/delete/${fileId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Error al eliminar el archivo.');
      }

      successMessage.set('Archivo eliminado con éxito.');
      files.update(currentFiles => currentFiles.filter(f => f._id !== fileId));
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
  }

  function cancelEditing() {
    editingFileId.set(null);
    editingFolderId.set(null);
    newFileName.set('');
    newFolderName.set('');
  }

  async function saveFileName(fileId) {
    if (!$newFileName.trim()) {
      errorMessage.set('El nombre del archivo no puede estar vacío.');
      setTimeout(() => errorMessage.set(''), 3000);
      return;
    }

    try {
      const response = await fetch(`${API_URL}/files/edit/${fileId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_filename: $newFileName }),
      });

      if (!response.ok) {
        throw new Error('Error al actualizar el nombre del archivo.');
      }

      await loadFolderContent($currentFolder || 'root');
      cancelEditing();
      successMessage.set('Nombre del archivo actualizado con éxito.');
      setTimeout(() => successMessage.set(''), 3000);
    } catch (error) {
      errorMessage.set(error.message);
    }
  }

  // --- Funciones de Utilidad ---
  function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  }

  function formatDate(dateString) {
    const options = { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };
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

  // --- Funciones de Ordenamiento ---
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
      
      if (order === 'asc') {
        return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      } else {
        return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
      }
    });
  }

  // --- Manejo de Drag and Drop ---
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

  // --- Funciones de Selección Múltiple ---
  
  /**
   * Alterna la selección de un archivo
   */
  function toggleFileSelection(fileId) {
    selectedFiles.update(set => {
      const newSet = new Set(set);
      if (newSet.has(fileId)) {
        newSet.delete(fileId);
      } else {
        newSet.add(fileId);
      }
      return newSet;
    });
    updateBulkActionsVisibility();
  }

  /**
   * Alterna la selección de una carpeta
   */
  function toggleFolderSelection(folderId) {
    selectedFolders.update(set => {
      const newSet = new Set(set);
      if (newSet.has(folderId)) {
        newSet.delete(folderId);
      } else {
        newSet.add(folderId);
      }
      return newSet;
    });
    updateBulkActionsVisibility();
  }

  /**
   * Seleccionar/deseleccionar todos los elementos
   */
  function toggleSelectAll() {
    selectAll.update(val => !val);
    
    if ($selectAll) {
      selectedFiles.set(new Set($files.map(f => f._id)));
      selectedFolders.set(new Set($folders.map(f => f._id)));
    } else {
      selectedFiles.set(new Set());
      selectedFolders.set(new Set());
    }
    updateBulkActionsVisibility();
  }

  /**
   * Actualiza la visibilidad de las acciones en lote
   */
  function updateBulkActionsVisibility() {
    const hasSelection = $selectedFiles.size > 0 || $selectedFolders.size > 0;
    showBulkActions.set(hasSelection);
    
    // Actualizar estado de "Seleccionar todo" - NO automático aquí
    // Solo se actualiza cuando el usuario hace click explícitamente
  }

  /**
   * Limpiar todas las selecciones
   */
  function clearSelections() {
    selectedFiles.set(new Set());
    selectedFolders.set(new Set());
    selectAll.set(false);
    showBulkActions.set(false);
  }

  /**
   * Eliminar elementos seleccionados
   */
  async function deleteSelectedItems() {
    if (!confirm(`¿Estás seguro de que quieres eliminar ${$selectedFiles.size + $selectedFolders.size} elemento(s)?`)) {
      return;
    }

    try {
      // Eliminar archivos seleccionados
      for (const fileId of $selectedFiles) {
        const response = await fetch(`${API_URL}/files/delete/${fileId}`, {
          method: 'DELETE'
        });
        if (!response.ok) {
          throw new Error(`Error al eliminar archivo ${fileId}`);
        }
      }

      // Eliminar carpetas seleccionadas
      for (const folderId of $selectedFolders) {
        const response = await fetch(`${API_URL}/folders/${folderId}`, {
          method: 'DELETE'
        });
        if (!response.ok) {
          throw new Error(`Error al eliminar carpeta ${folderId}`);
        }
      }

      successMessage.set('Elementos eliminados correctamente');
      clearSelections();
      await loadFolderContent($currentFolder);
    } catch (error) {
      errorMessage.set(error.message);
    }
  }

  /**
   * Mostrar modal para mover elementos seleccionados
   */
  async function moveSelectedItems() {
    if ($selectedFiles.size === 0 && $selectedFolders.size === 0) {
      return;
    }

    // Por ahora, mover a la carpeta raíz como demostración
    const targetFolder = prompt('¿A qué carpeta quieres mover los elementos? (ID de carpeta o "root" para raíz):');
    if (!targetFolder) {
      return;
    }

    try {
      // Mover archivos seleccionados
      for (const fileId of $selectedFiles) {
        const response = await fetch(`${API_URL}/files/${fileId}/move`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            folder_id: targetFolder === 'root' ? null : targetFolder
          })
        });
        if (!response.ok) {
          throw new Error(`Error al mover archivo ${fileId}`);
        }
      }

      // Mover carpetas seleccionadas
      for (const folderId of $selectedFolders) {
        const response = await fetch(`${API_URL}/folders/${folderId}/move`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            parent_folder_id: targetFolder === 'root' ? null : targetFolder
          })
        });
        if (!response.ok) {
          throw new Error(`Error al mover carpeta ${folderId}`);
        }
      }

      successMessage.set(`${$selectedFiles.size + $selectedFolders.size} elemento(s) movido(s) correctamente`);
      clearSelections();
      await loadFolderContent($currentFolder);
    } catch (error) {
      errorMessage.set(error.message);
    }
  }

  /**
   * Copiar elementos seleccionados
   */
  async function copySelectedItems() {
    if ($selectedFiles.size === 0 && $selectedFolders.size === 0) {
      return;
    }

    // Por ahora, copiar a la carpeta raíz como demostración
    const targetFolder = prompt('¿A qué carpeta quieres copiar los elementos? (ID de carpeta o "root" para raíz):');
    if (!targetFolder) {
      return;
    }

    try {
      // Copiar archivos seleccionados
      for (const fileId of $selectedFiles) {
        const response = await fetch(`${API_URL}/files/${fileId}/copy`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            folder_id: targetFolder === 'root' ? null : targetFolder
          })
        });
        if (!response.ok) {
          throw new Error(`Error al copiar archivo ${fileId}`);
        }
      }

      // Copiar carpetas seleccionadas
      for (const folderId of $selectedFolders) {
        const response = await fetch(`${API_URL}/folders/${folderId}/copy`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            parent_folder_id: targetFolder === 'root' ? null : targetFolder
          })
        });
        if (!response.ok) {
          throw new Error(`Error al copiar carpeta ${folderId}`);
        }
      }

      successMessage.set(`${$selectedFiles.size + $selectedFolders.size} elemento(s) copiado(s) correctamente`);
      clearSelections();
      await loadFolderContent($currentFolder);
    } catch (error) {
      errorMessage.set(error.message);
    }
  }

  // --- Funciones de Preview ---
  
  /**
   * Determina si un archivo se puede previsualizar
   */
  function canPreview(fileType) {
    const previewableTypes = [
      'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml',
      'text/plain', 'text/html', 'text/css', 'text/javascript', 'application/javascript',
      'application/json', 'text/markdown', 'text/csv',
      'application/pdf'
    ];
    
    return previewableTypes.includes(fileType.toLowerCase());
  }

  /**
   * Abre el preview de un archivo
   */
  async function openPreview(file) {
    previewFile.set(file);
    previewContent.set('');
    previewError.set('');
    showPreview.set(true);
    
    try {
      const fileType = file.file_type.toLowerCase();
      
      // Archivos de imagen
      if (fileType.startsWith('image/')) {
        previewContent.set(`${API_URL}/files/download/${file._id}`);
        return;
      }
      
      // PDF
      if (fileType === 'application/pdf') {
        previewContent.set(`${API_URL}/files/download/${file._id}`);
        return;
      }
      
      // Archivos de texto
      if (fileType.startsWith('text/') || 
          fileType === 'application/json' || 
          fileType === 'application/javascript') {
        
        const response = await fetch(`${API_URL}/files/download/${file._id}`);
        if (!response.ok) {
          throw new Error('Error al cargar el archivo');
        }
        
        const text = await response.text();
        previewContent.set(text);
        return;
      }
      
    } catch (error) {
      previewError.set('Error al cargar la previsualización: ' + error.message);
    }
  }

  /**
   * Cierra el preview
   */
  function closePreview() {
    showPreview.set(false);
    previewFile.set(null);
    previewContent.set('');
    previewError.set('');
  }

  // --- Reactive Statements ---
  $: sortedFiles = sortItems($files, $sortBy, $sortOrder);
  $: sortedFolders = sortItems($folders, $sortBy, $sortOrder);
  
  // Actualizar estado del checkbox "Seleccionar todo"
  $: {
    const totalItems = $files.length + $folders.length;
    const selectedItems = $selectedFiles.size + $selectedFolders.size;
    if (totalItems > 0 && selectedItems === totalItems && !$selectAll) {
      selectAll.set(true);
    } else if (selectedItems === 0 && $selectAll) {
      selectAll.set(false);
    }
  }
  
  // Limpiar selecciones cuando cambie la carpeta o el contenido
  $: if ($currentFolder) {
    clearSelections();
  }

  // --- Lifecycle ---
  onMount(() => {
    loadFolderContent();
  });

  // --- Search reactivity ---
  let debounceTimer;
  $: if ($searchTerm !== undefined && $currentFolder) {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      searchFiles();
    }, 300);
  }
</script>

<main class="bg-gray-50 min-h-screen">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    
    <!-- Header -->
    <header class="mb-8">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-4xl font-bold text-gray-900">Mi Drive</h1>
          <p class="text-gray-600 mt-1">Gestiona tus archivos y carpetas de forma sencilla</p>
        </div>
        <div class="flex items-center space-x-4">
          <!-- View Mode Toggle -->
          <div class="flex border rounded-lg overflow-hidden">
            <button 
              class="px-3 py-2 text-sm {$viewMode === 'list' ? 'bg-blue-500 text-white' : 'bg-white text-gray-700'}"
              on:click={() => viewMode.set('list')}
            >
              📋 Lista
            </button>
            <button 
              class="px-3 py-2 text-sm {$viewMode === 'grid' ? 'bg-blue-500 text-white' : 'bg-white text-gray-700'}"
              on:click={() => viewMode.set('grid')}
            >
              ⊞ Cuadrícula
            </button>
          </div>
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
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0">
        
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
            <div class="flex items-center space-x-3 bg-blue-50 px-3 py-2 rounded-lg border border-blue-200">
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
                  🗑️
                </button>
                
                <button
                  on:click={moveSelectedItems}
                  class="p-1.5 bg-green-600 text-white text-xs rounded hover:bg-green-700 transition-colors"
                  title="Mover seleccionados"
                >
                  📁
                </button>
                
                <button
                  on:click={copySelectedItems}
                  class="p-1.5 bg-purple-600 text-white text-xs rounded hover:bg-purple-700 transition-colors"
                  title="Copiar seleccionados"
                >
                  📋
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
      class="bg-white p-6 rounded-lg shadow-sm mb-6 border-2 border-dashed transition-all duration-300 {isDropping ? 'border-blue-500 bg-blue-50' : 'border-gray-300'}"
      on:dragenter={handleDragEnter}
      on:dragleave={handleDragLeave}
      on:dragover|preventDefault
      on:drop={handleDrop}
    >
      <div class="text-center">
        <div class="text-4xl mb-4">📤</div>
        <h3 class="text-lg font-medium text-gray-900 mb-2">Subir archivos</h3>
        <p class="text-gray-600 mb-4">Arrastra archivos aquí o selecciona desde tu computadora</p>
        <label for="file-upload" class="inline-flex items-center px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 cursor-pointer transition-colors">
          📎 Seleccionar Archivos
        </label>
        <input id="file-upload" type="file" class="hidden" on:change={handleFileUpload} multiple />
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
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-16">
                  <input
                    type="checkbox"
                    bind:checked={$selectAll}
                    on:change={toggleSelectAll}
                    class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    title="Seleccionar todo"
                  />
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nombre</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tamaño</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Modificado</th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Acciones</th>
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
                  <td class="px-6 py-4 whitespace-nowrap cursor-pointer" on:click={() => navigateToFolder(folder._id)}>
                    <div class="flex items-center">
                      <span class="text-2xl mr-3">📁</span>
                      <span class="text-sm font-medium text-gray-900">{folder.name}</span>
                    </div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">—</td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{formatDate(folder.created_date)}</td>
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
                          class="border rounded px-2 py-1 text-sm"
                          on:keydown={(e) => e.key === 'Enter' && saveFileName(file._id)}
                          on:blur={() => saveFileName(file._id)}
                        />
                        <button on:click={cancelEditing} class="text-xs text-gray-500 ml-2">Cancelar</button>
                      </div>
                    {:else}
                      <div class="flex items-center">
                        <span class="text-xl mr-3">{getFileIcon(file.file_type)}</span>
                        <span class="text-sm font-medium text-gray-900">{file.filename}</span>
                      </div>
                    {/if}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{formatBytes(file.size)}</td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{formatDate(file.upload_date)}</td>
                  <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    {#if canPreview(file.file_type)}
                      <button on:click={() => openPreview(file)} class="text-blue-600 hover:text-blue-900 mr-3">👁️ Preview</button>
                    {/if}
                    <button on:click={() => startEditingFile(file)} class="text-indigo-600 hover:text-indigo-900 mr-3">✏️ Editar</button>
                    <a href="{API_URL}/files/download/{file._id}" target="_blank" class="text-green-600 hover:text-green-900 mr-3" download>⬇️ Descargar</a>
                    <button on:click={() => handleDeleteFile(file._id)} class="text-red-600 hover:text-red-900">🗑️ Eliminar</button>
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
                <div class="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                  <div class="text-center">
                    <div class="text-4xl mb-2">{getFileIcon(file.file_type)}</div>
                    {#if $editingFileId === file._id}
                      <input
                        type="text"
                        bind:value={$newFileName}
                        class="w-full text-xs border rounded px-1 py-0.5 mb-1"
                        on:keydown={(e) => e.key === 'Enter' && saveFileName(file._id)}
                        on:blur={() => saveFileName(file._id)}
                      />
                    {:else}
                      <p class="text-sm font-medium text-gray-900 truncate mb-1">{file.filename}</p>
                    {/if}
                    <p class="text-xs text-gray-500">{formatBytes(file.size)}</p>
                    <p class="text-xs text-gray-400">{formatDate(file.upload_date)}</p>
                  </div>
                  
                  <!-- File Actions -->
                  <div class="mt-3 flex justify-center space-x-2">
                    {#if canPreview(file.file_type)}
                      <button on:click={() => openPreview(file)} class="text-xs text-blue-600 hover:text-blue-900" title="Preview">👁️</button>
                    {/if}
                    <button on:click={() => startEditingFile(file)} class="text-xs text-indigo-600 hover:text-indigo-900">✏️</button>
                    <a href="{API_URL}/files/download/{file._id}" target="_blank" class="text-xs text-green-600 hover:text-green-900" download>⬇️</a>
                    <button on:click={() => handleDeleteFile(file._id)} class="text-xs text-red-600 hover:text-red-900">🗑️</button>
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
          <div class="bg-blue-500 text-white px-4 py-3 rounded-lg shadow-lg flex items-center space-x-3">
            <div class="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
            <span class="font-medium">Cargando...</span>
          </div>
        {/if}
      </div>
    {/if}

    <!-- Success Popup -->
    {#if $successMessage}
      <div class="success-popup">
        <div class="bg-green-500 text-white px-4 py-3 rounded-lg shadow-lg flex items-center space-x-3">
          <div class="text-lg">✅</div>
          <span class="font-medium">{$successMessage}</span>
        </div>
      </div>
    {/if}

    <!-- Error Popup -->
    {#if $errorMessage}
      <div class="error-popup">
        <div class="bg-red-500 text-white px-4 py-3 rounded-lg shadow-lg flex items-center space-x-3">
          <div class="text-lg">❌</div>
          <span class="font-medium">{$errorMessage}</span>
        </div>
      </div>
    {/if}
  </div>

  <!-- Modal de Preview -->
  {#if $showPreview}
    <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 preview-modal" on:click={closePreview}>
      <div class="bg-white rounded-lg shadow-xl max-w-4xl max-h-[90vh] w-full mx-4 overflow-hidden preview-modal-content" on:click={(e) => e.stopPropagation()}>
        <!-- Header del modal -->
        <div class="flex items-center justify-between p-4 border-b border-gray-200">
          <div class="flex items-center space-x-3">
            <span class="text-2xl">{$previewFile ? getFileIcon($previewFile.file_type) : '📄'}</span>
            <div>
              <h3 class="text-lg font-semibold text-gray-900">{$previewFile?.filename || 'Preview'}</h3>
              <p class="text-sm text-gray-500">{$previewFile ? formatBytes($previewFile.size) : ''}</p>
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
                <pre class="text-sm text-gray-800 whitespace-pre-wrap overflow-auto max-h-[60vh] font-mono">{$previewContent}</pre>
              </div>
            {:else}
              <!-- Tipo no soportado -->
              <div class="text-center py-8">
                <div class="text-4xl mb-4">📄</div>
                <p class="text-gray-600">Este tipo de archivo no se puede previsualizar</p>
                <a
                  href="{API_URL}/files/download/{$previewFile._id}"
                  target="_blank"
                  class="inline-block mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  download
                >
                  ⬇️ Descargar archivo
                </a>
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
            <a
              href="{API_URL}/files/download/{$previewFile?._id}"
              target="_blank"
              class="px-3 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition-colors"
              download
            >
              ⬇️ Descargar
            </a>
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
</main>

<style>
  /* Custom animations */
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
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
    background: linear-gradient(90deg, rgba(255,255,255,0.9) 0%, rgba(255,255,255,1) 50%, rgba(255,255,255,0.9) 100%);
    box-shadow: inset 0 1px 2px rgba(255,255,255,0.3);
    position: relative;
  }
  
  .upload-progress-bar::after {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
    animation: shimmer 2s infinite;
  }
  
  @keyframes shimmer {
    0% { left: -100%; }
    100% { left: 100%; }
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
