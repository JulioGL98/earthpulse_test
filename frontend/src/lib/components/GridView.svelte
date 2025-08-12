<script>
  import {
    selectAll,
    selectedFiles,
    selectedFolders,
    showBulkActions,
  } from '$lib/stores/selection.js';
  import { searchTerm } from '$lib/stores/fileManager.js';
  import { getFileIcon, formatBytes, formatDate } from '$lib/utils/formatters.js';

  export let sortedFolders;
  export let sortedFiles;
  export let toggleSelectAll;
  export let toggleFolderSelection;
  export let navigateToFolder;
  export let deleteFolderHandler;
  export let toggleFileSelection;
  export let isImageFile;
  export let loadThumbnail;
  export let editingFileId;
  export let newFileName;
  export let saveFileName;
  export let canPreview;
  export let openPreview;
  export let startEditingFile;
  export let downloadFileHandler;
  export let handleDeleteFile;
</script>

<div class="p-6">
  <div class="flex items-center justify-between mb-4">
    <div class="flex items-center space-x-3">
      <input
        type="checkbox"
        id="select-all-checkbox"
        bind:checked={$selectAll}
        on:change={toggleSelectAll}
        class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
      />
      <label for="select-all-checkbox" class="text-sm text-gray-600"> Seleccionar todo </label>
    </div>
    {#if $showBulkActions}
      <div class="text-sm text-gray-600">
        {$selectedFiles.size + $selectedFolders.size} elemento(s) seleccionado(s)
      </div>
    {/if}
  </div>

  <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
    {#each sortedFolders as folder (folder._id)}
      <div class="relative group">
        <input
          type="checkbox"
          id="folder-checkbox-{folder._id}"
          checked={$selectedFolders.has(folder._id)}
          on:change={() => toggleFolderSelection(folder._id)}
          class="absolute top-2 left-2 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded z-10"
          on:click={(e) => e.stopPropagation()}
          aria-label="Seleccionar carpeta {folder.name}"
        />
        <button
          type="button"
          class="bg-gray-50 rounded-lg p-4 hover:bg-gray-100 cursor-pointer transition-colors w-full text-left"
          on:click={() => navigateToFolder(folder._id)}
          aria-label="Abrir carpeta {folder.name}"
        >
          <div class="text-center">
            <div class="text-4xl mb-2">📁</div>
            <p class="text-sm font-medium text-gray-900 truncate">{folder.name}</p>
            <p class="text-xs text-gray-500 mt-1">{formatDate(folder.created_date)}</p>
          </div>
        </button>
        <button
          type="button"
          on:click={() => deleteFolderHandler(folder._id)}
          class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs transition-opacity"
          aria-label="Eliminar carpeta {folder.name}"
        >
          ✕
        </button>
      </div>
    {/each}
    {#each sortedFiles as file (file._id)}
      <div class="relative group">
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
              on:click={() => downloadFileHandler(file._id, file.filename)}
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
