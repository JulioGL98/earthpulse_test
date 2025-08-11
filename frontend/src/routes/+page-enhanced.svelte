<script>
  import { onMount } from 'svelte';
  import { writable } from 'svelte/store';

  // --- Estado de la Aplicación ---
  let files = writable([]);
  let folders = writable([]);
  let currentFolder = writable(null);
  let folderPath = writable('/');
  let isLoading = writable(true);
  let errorMessage = writable('');
  let successMessage = writable('');
  let editingFileId = writable(null);
  let editingFolderId = writable(null);
  let newFileName = writable('');
  let newFolderName = writable('');
  let searchTerm = writable('');
  let sortBy = writable('name');
  let sortOrder = writable('asc');
  let viewMode = writable('list'); // 'list' or 'grid'
  let showCreateFolder = writable(false);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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
      currentFolder.set(folderId === 'root' ? null : folderId);
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
      await loadFolderContent($currentFolder);
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
    await loadFolderContent(folderId);
    // Actualizar la ruta de navegación
    if (folderId === 'root' || !folderId) {
      folderPath.set('/');
    } else {
      try {
        const response = await fetch(`${API_URL}/folders/${folderId}`);
        if (response.ok) {
          const folder = await response.json();
          folderPath.set(folder.path);
        }
      } catch (error) {
        console.warn('No se pudo actualizar la ruta:', error);
      }
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
      await loadFolderContent($currentFolder);
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
      await loadFolderContent($currentFolder);
    } catch (error) {
      errorMessage.set(error.message);
    } finally {
      setTimeout(() => successMessage.set(''), 3000);
    }
  }

  /**
   * Maneja la subida de archivos
   */
  async function handleFileUpload(e) {
    const fileInput = e.target.files[0];
    if (!fileInput) return;

    const formData = new FormData();
    formData.append('file', fileInput);
    
    // Agregar folder_id si estamos en una carpeta específica
    if ($currentFolder && $currentFolder !== 'root') {
      formData.append('folder_id', $currentFolder);
    }

    isLoading.set(true);
    successMessage.set('');
    errorMessage.set('');

    try {
      const response = await fetch(`${API_URL}/files/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error al subir el archivo.');
      }
      
      successMessage.set('¡Archivo subido con éxito!');
      await loadFolderContent($currentFolder);
    } catch (error) {
      errorMessage.set(error.message);
    } finally {
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

      await loadFolderContent($currentFolder);
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
    const droppedFiles = e.dataTransfer.files;
    if (droppedFiles.length > 0) {
      const fakeEvent = { target: { files: droppedFiles } };
      await handleFileUpload(fakeEvent);
    }
  }

  // --- Reactive Statements ---
  $: sortedFiles = sortItems($files, $sortBy, $sortOrder);
  $: sortedFolders = sortItems($folders, $sortBy, $sortOrder);

  // --- Lifecycle ---
  onMount(() => {
    loadFolderContent();
  });

  // --- Search reactivity ---
  let debounceTimer;
  $: {
    if (debounceTimer) clearTimeout(debounceTimer);
    if ($searchTerm !== undefined) {
      debounceTimer = setTimeout(() => {
        searchFiles();
      }, 300);
    }
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
    </nav>

    <!-- Toolbar -->
    <div class="bg-white rounded-lg shadow-sm p-4 mb-6">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0">
        
        <!-- Search and Create Controls -->
        <div class="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-4">
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

    <!-- Status Messages -->
    {#if $isLoading}
      <div class="bg-blue-100 border border-blue-300 text-blue-700 p-4 rounded-lg mb-4">
        <div class="flex items-center">
          <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-700 mr-2"></div>
          Cargando...
        </div>
      </div>
    {/if}

    {#if $successMessage}
      <div class="bg-green-100 border border-green-300 text-green-700 p-4 rounded-lg mb-4">
        ✅ {$successMessage}
      </div>
    {/if}

    {#if $errorMessage}
      <div class="bg-red-100 border border-red-300 text-red-700 p-4 rounded-lg mb-4">
        ❌ {$errorMessage}
      </div>
    {/if}

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
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nombre</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tamaño</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Modificado</th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Acciones</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              
              <!-- Folders -->
              {#each sortedFolders as folder (folder._id)}
                <tr class="hover:bg-gray-50 cursor-pointer">
                  <td class="px-6 py-4 whitespace-nowrap" on:click={() => navigateToFolder(folder._id)}>
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
                    <button on:click={() => startEditingFile(file)} class="text-indigo-600 hover:text-indigo-900 mr-3">✏️ Editar</button>
                    <a href="{API_URL}/files/download/{file._id}" target="_blank" class="text-green-600 hover:text-green-900 mr-3" download>⬇️ Descargar</a>
                    <button on:click={() => handleDeleteFile(file._id)} class="text-red-600 hover:text-red-900">🗑️ Eliminar</button>
                  </td>
                </tr>
              {/each}

              {#if sortedFolders.length === 0 && sortedFiles.length === 0}
                <tr>
                  <td colspan="4" class="text-center py-12 text-gray-500">
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
          <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
            
            <!-- Folders -->
            {#each sortedFolders as folder (folder._id)}
              <div class="relative group">
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
</main>

<style>
  /* Custom animations */
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
  
  .fade-in {
    animation: fadeIn 0.3s ease-out;
  }
</style>
