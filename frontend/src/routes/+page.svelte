<script>
  import { onMount, onDestroy } from 'svelte';
  import { get, writable } from 'svelte/store';

  // Stores
  import {
    authToken,
    authUser,
    showAuthScreen,
    authMode,
    authUsername,
    authPassword,
    authError,
    authLoading,
    saveToken,
    loadToken,
    logout as authLogout,
  } from '$lib/stores/auth.js';
  import {
    files,
    folders,
    currentFolder,
    folderPath,
    folderHistory,
    currentFolderInfo,
    searchTerm,
  } from '$lib/stores/fileManager.js';
  import {
    isLoading,
    errorMessage,
    successMessage,
    uploadProgress,
    viewMode,
    showCreateFolder,
    showPreview,
    previewFile,
    previewContent,
    previewError,
    showFolderSelector,
    allFolders,
    selectorCurrentFolder,
    selectedTargetFolder,
    selectorMode,
  } from '$lib/stores/ui.js';
  import {
    selectedFiles,
    selectedFolders,
    selectAll,
    showBulkActions,
    clearSelections,
  } from '$lib/stores/selection.js';

  // API Service
  import * as api from '$lib/services/api.js';

  // Components
  import AuthScreen from '$lib/components/AuthScreen.svelte';
  import Header from '$lib/components/Header.svelte';
  import Breadcrumb from '$lib/components/Breadcrumb.svelte';
  import Toolbar from '$lib/components/Toolbar.svelte';
  import FileUploadArea from '$lib/components/FileUploadArea.svelte';
  import CreateFolderModal from '$lib/components/CreateFolderModal.svelte';
  import ListView from '$lib/components/ListView.svelte';
  import GridView from '$lib/components/GridView.svelte';
  import Notifications from '$lib/components/Notifications.svelte';
  import PreviewModal from '$lib/components/PreviewModal.svelte';
  import FolderSelectorModal from '$lib/components/FolderSelectorModal.svelte';

  // Utils
  import { isImageFile } from '$lib/utils/formatters.js';

  // --- Auth State ---
  function handleKeyPress(event) {
    if (event.key === 'Enter') {
      event.preventDefault();
      handleAuthSubmit();
    }
  }

  async function handleAuthSubmit() {
    authError.set('');
    if (!get(authUsername).trim() || !get(authPassword).trim()) {
      authError.set('Usuario y contraseña requeridos');
      return;
    }

    const maxRetries = 5;
    let retryCount = 0;

    authLoading.set(true);

    while (retryCount < maxRetries) {
      try {
        const credentials = {
          username: get(authUsername).trim(),
          password: get(authPassword),
        };
        const data =
          get(authMode) === 'login'
            ? await api.login(credentials.username, credentials.password)
            : await api.register(credentials.username, credentials.password);

        if (data.access_token) {
          saveToken(data.access_token);
          authUser.set(credentials.username);
          showAuthScreen.set(false);
          authPassword.set('');
          authError.set('');
          await loadFolderContent('root');
          return;
        } else {
          throw new Error('Token no recibido');
        }
      } catch (e) {
        console.log('Error en intento de login:', e.message);
        if (
          (e.message.toLowerCase().includes('failed to fetch') ||
            e.message.toLowerCase().includes('network error') ||
            e.message.toLowerCase().includes('fetch')) &&
          retryCount < maxRetries - 1
        ) {
          retryCount++;
          const waitTime = Math.min(1000 * Math.pow(2, retryCount - 1), 5000);
          await new Promise((resolve) => setTimeout(resolve, waitTime));
          continue;
        } else {
          if (retryCount >= maxRetries - 1) {
            authError.set(
              'No se pudo conectar al servidor. Verifica tu conexión e inténtalo de nuevo.'
            );
          } else {
            authError.set(e.message);
          }
          break;
        }
      }
    }
    authLoading.set(false);
  }

  function logout() {
    authLogout();
    files.set([]);
    folders.set([]);
    clearSelections();
  }

  onMount(async () => {
    loadToken();
    if (get(authToken)) {
      try {
        // Try a protected endpoint to validate token
        await api.getFolderContent('root');
        authUser.set(''); // Username not in simple token; could be decoded
        showAuthScreen.set(false);
        await loadFolderContent('root');
      } catch {
        logout();
      }
    } else {
      isLoading.set(false);
    }
  });

  // --- App State ---
  let editingFileId = writable(null);
  let newFileName = writable('');
  let originalFileName = writable('');
  let newFolderName = writable('');
  let sortBy = writable('name');
  let sortOrder = writable('asc');

  async function loadFolderContent(folderId = 'root') {
    if (get(showAuthScreen)) return;
    isLoading.set(true);
    errorMessage.set('');
    clearThumbnailCache();

    try {
      const data = await api.getFolderContent(folderId);
      files.set(data.files);
      folders.set(data.folders);
      currentFolder.set(folderId);
    } catch (error) {
      errorMessage.set(error.message);
    } finally {
      isLoading.set(false);
    }
  }

  async function searchFilesHandler() {
    if (get(showAuthScreen)) return;
    const term = get(searchTerm).trim();
    if (!term) {
      await loadFolderContent(get(currentFolder) || 'root');
      return;
    }
    isLoading.set(true);
    try {
      const data = await api.searchFiles(term, get(currentFolder));
      files.set(data);
      folders.set([]); // Search results only contain files
    } catch (error) {
      errorMessage.set(error.message);
    } finally {
      isLoading.set(false);
    }
  }

  async function navigateToFolder(folderId) {
    if (get(currentFolder) !== folderId && get(currentFolder) !== 'root') {
      folderHistory.update((h) => [...h, { id: get(currentFolder), info: get(currentFolderInfo) }]);
    }
    await loadFolderContent(folderId);
    if (folderId === 'root' || !folderId) {
      folderPath.set('/');
      currentFolderInfo.set(null);
    } else {
      try {
        const folder = await api.getFolderDetails(folderId);
        if (folder) {
          folderPath.set(folder.path);
          currentFolderInfo.set(folder);
        }
      } catch {}
    }
  }

  async function navigateBack() {
    const info = get(currentFolderInfo);
    if (info && info.parent_folder_id) {
      await navigateToFolder(info.parent_folder_id || 'root');
    } else {
      await navigateToFolder('root');
    }
  }

  async function createFolderHandler() {
    const name = get(newFolderName).trim();
    if (!name) {
      errorMessage.set('El nombre de la carpeta no puede estar vacío.');
      setTimeout(() => errorMessage.set(''), 3000);
      return;
    }
    try {
      await api.createFolder(name, get(currentFolder));
      successMessage.set('Carpeta creada con éxito.');
      newFolderName.set('');
      showCreateFolder.set(false);
      await loadFolderContent(get(currentFolder) || 'root');
    } catch (error) {
      errorMessage.set(error.message);
    } finally {
      setTimeout(() => {
        successMessage.set('');
        errorMessage.set('');
      }, 3000);
    }
  }

  async function deleteFolderHandler(folderId) {
    if (!confirm('¿Estás seguro de que quieres eliminar esta carpeta y todo su contenido?')) return;
    try {
      await api.deleteFolder(folderId);
      successMessage.set('Carpeta eliminada con éxito.');
      await loadFolderContent(get(currentFolder) || 'root');
    } catch (error) {
      errorMessage.set(error.message);
    } finally {
      setTimeout(() => successMessage.set(''), 3000);
    }
  }

  async function handleFileUpload(e) {
    const filesArr = Array.from(e.target.files || e.dataTransfer?.files || []);
    if (filesArr.length === 0) return;

    const currentFolderValue = get(currentFolder);
    isLoading.set(true);
    successMessage.set('');
    errorMessage.set('');
    let uploadedCount = 0;

    try {
      for (let i = 0; i < filesArr.length; i++) {
        const file = filesArr[i];
        uploadProgress.set({
          fileName: file.name,
          progress: 0,
          totalFiles: filesArr.length,
          currentFile: i + 1,
        });

        await api.uploadFileWithProgress(file, currentFolderValue, (progress) => {
          uploadProgress.update((c) => ({ ...c, progress: Math.min(progress, 100) }));
        });
        uploadedCount++;

        if (i < filesArr.length - 1) await new Promise((r) => setTimeout(r, 500));
      }

      uploadProgress.set(null);
      successMessage.set(
        `¡${uploadedCount} archivo${uploadedCount > 1 ? 's' : ''} subido${
          uploadedCount > 1 ? 's' : ''
        } con éxito!`
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
      const fileInput = document.getElementById('file-upload');
      if (fileInput) fileInput.value = '';
      isLoading.set(false);
      setTimeout(() => {
        successMessage.set('');
        errorMessage.set('');
      }, 3000);
    }
  }

  async function handleDeleteFile(fileId) {
    if (!confirm('¿Estás seguro de que quieres eliminar este archivo?')) return;
    try {
      await api.deleteFile(fileId);
      successMessage.set('Archivo eliminado con éxito.');
      files.update((cf) => cf.filter((f) => f._id !== fileId));
    } catch (error) {
      errorMessage.set(error.message);
    } finally {
      setTimeout(() => successMessage.set(''), 3000);
    }
  }

  function startEditingFile(file) {
    editingFileId.set(file._id);
    newFileName.set(file.filename);
    originalFileName.set(file.filename);
  }

  function cancelEditing() {
    editingFileId.set(null);
    newFileName.set('');
    originalFileName.set('');
    newFolderName.set('');
  }

  async function saveFileName(fileId, forceValidation = false) {
    const trimmedName = get(newFileName).trim();
    const originalName = get(originalFileName).trim();
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
      await api.renameFile(fileId, trimmedName);
      await loadFolderContent(get(currentFolder) || 'root');
      cancelEditing();
      successMessage.set('Nombre del archivo actualizado con éxito.');
      setTimeout(() => successMessage.set(''), 3000);
    } catch (error) {
      errorMessage.set(error.message);
    }
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
    if (get(selectAll)) {
      selectedFiles.set(new Set(get(files).map((f) => f._id)));
      selectedFolders.set(new Set(get(folders).map((f) => f._id)));
    } else {
      selectedFiles.set(new Set());
      selectedFolders.set(new Set());
    }
    updateBulkActionsVisibility();
  }

  function updateBulkActionsVisibility() {
    const hasSelection = get(selectedFiles).size > 0 || get(selectedFolders).size > 0;
    showBulkActions.set(hasSelection);
  }

  async function deleteSelectedItems() {
    if (
      !confirm(
        `¿Estás seguro de que quieres eliminar ${
          get(selectedFiles).size + get(selectedFolders).size
        } elemento(s)?`
      )
    )
      return;
    try {
      for (const fileId of get(selectedFiles)) {
        await api.deleteFile(fileId);
      }
      for (const folderId of get(selectedFolders)) {
        await api.deleteFolder(folderId);
      }
      successMessage.set('Elementos eliminados correctamente');
      clearSelections();
      await loadFolderContent(get(currentFolder));
    } catch (e) {
      errorMessage.set(e.message);
    }
  }

  async function moveSelectedItems() {
    if (get(selectedFiles).size === 0 && get(selectedFolders).size === 0) return;
    await openFolderSelector('move');
  }

  async function copySelectedItems() {
    if (get(selectedFiles).size === 0 && get(selectedFolders).size === 0) return;
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
      const content = await api.getFilePreviewContent(file);
      previewContent.set(content);
    } catch (e) {
      previewError.set('Error al cargar la previsualización: ' + e.message);
    }
  }

  function closePreview() {
    const currentContent = get(previewContent);
    if (currentContent && currentContent.startsWith('blob:')) URL.revokeObjectURL(currentContent);
    showPreview.set(false);
    previewFile.set(null);
    previewContent.set('');
    previewError.set('');
  }

  async function downloadFileHandler(fileId, filename) {
    try {
      await api.downloadFile(fileId, filename);
    } catch (error) {
      errorMessage.set('Error al descargar el archivo: ' + error.message);
      setTimeout(() => errorMessage.set(''), 3000);
    }
  }

  const thumbnailCache = new Map();

  async function loadThumbnail(fileId) {
    if (thumbnailCache.has(fileId)) {
      return thumbnailCache.get(fileId);
    }
    try {
      const url = await api.getFilePreviewContent({ _id: fileId, file_type: 'image/' });
      thumbnailCache.set(fileId, url);
      return url;
    } catch (error) {
      console.error('Error loading thumbnail:', error);
      return null;
    }
  }

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
      const fs = await api.getFolders(folderId);
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
    const targetFolder = get(selectedTargetFolder);
    const targetFolderId = targetFolder ? targetFolder._id : null;
    const mode = get(selectorMode);
    const isMove = mode === 'move';

    try {
      const filePromises = Array.from(get(selectedFiles)).map((fileId) =>
        isMove ? api.moveFile(fileId, targetFolderId) : api.copyFile(fileId, targetFolderId)
      );
      const folderPromises = Array.from(get(selectedFolders)).map((folderId) =>
        isMove ? api.moveFolder(folderId, targetFolderId) : api.copyFolder(folderId, targetFolderId)
      );

      await Promise.all([...filePromises, ...folderPromises]);

      const targetName = targetFolder ? targetFolder.name : 'Raíz';
      const actionName = isMove ? 'movido(s)' : 'copiado(s)';
      successMessage.set(
        `${get(selectedFiles).size + get(selectedFolders).size} elemento(s) ${actionName} a "${targetName}" correctamente`
      );
      if (isMove) clearSelections();
      closeFolderSelector();
      await loadFolderContent(get(currentFolder));
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
    const currentContent = get(previewContent);
    if (currentContent && currentContent.startsWith('blob:')) URL.revokeObjectURL(currentContent);
    clearThumbnailCache();
  });

  let debounceTimer;
  $: if ($searchTerm !== undefined && $currentFolder !== undefined) {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      searchFilesHandler();
    }, 300);
  }
</script>

{#if $showAuthScreen}
  <AuthScreen {handleAuthSubmit} {handleKeyPress} />
{:else}
  <main class="bg-gray-50 min-h-screen">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <Header {logout} />
      <Breadcrumb {navigateToFolder} {navigateBack} />
      <Toolbar
        {deleteSelectedItems}
        {moveSelectedItems}
        {copySelectedItems}
        bind:sortBy
        bind:sortOrder
      />
      <FileUploadArea
        {isDropping}
        {handleDragEnter}
        {handleDragLeave}
        {handleDrop}
        {handleFileUpload}
      />
      <CreateFolderModal bind:newFolderName {createFolderHandler} />

      <div class="bg-white rounded-lg shadow-sm overflow-hidden">
        {#if $viewMode === 'list'}
          <ListView
            {sortedFolders}
            {sortedFiles}
            {toggleSelectAll}
            {selectedFolders}
            {toggleFolderSelection}
            {navigateToFolder}
            {deleteFolderHandler}
            {selectedFiles}
            {toggleFileSelection}
            bind:editingFileId
            bind:newFileName
            {saveFileName}
            {cancelEditing}
            {canPreview}
            {openPreview}
            {startEditingFile}
            {downloadFileHandler}
            {handleDeleteFile}
          />
        {:else}
          <GridView
            {sortedFolders}
            {sortedFiles}
            {toggleSelectAll}
            {toggleFolderSelection}
            {navigateToFolder}
            {deleteFolderHandler}
            {toggleFileSelection}
            {isImageFile}
            {loadThumbnail}
            bind:editingFileId
            bind:newFileName
            {saveFileName}
            {canPreview}
            {openPreview}
            {startEditingFile}
            {downloadFileHandler}
            {handleDeleteFile}
          />
        {/if}
      </div>

      <div class="mt-8 text-center text-sm text-gray-500">
        {sortedFolders.length} carpeta{sortedFolders.length !== 1 ? 's' : ''},
        {sortedFiles.length} archivo{sortedFiles.length !== 1 ? 's' : ''}
        {#if $searchTerm}
          · Resultados de búsqueda para "{$searchTerm}"
        {/if}
      </div>
    </div>

    <Notifications />
    <PreviewModal {closePreview} {downloadFileHandler} />
    <FolderSelectorModal
      {closeFolderSelector}
      {navigateToFolderInSelector}
      {selectTargetFolder}
      {confirmAction}
    />
  </main>
{/if}

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

  /* Progress bar styles */
  :global(.progress-bar) {
    transition: width 0.3s ease-out;
    animation: progressFill 0.5s ease-out;
  }
</style>
