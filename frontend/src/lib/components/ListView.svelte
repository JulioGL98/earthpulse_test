<script>
  import { selectAll } from '$lib/stores/selection.js';
  import { searchTerm } from '$lib/stores/fileManager.js';
  import { getFileIcon, formatBytes, formatDate } from '$lib/utils/formatters.js';

  export let sortedFolders;
  export let sortedFiles;
  export let toggleSelectAll;
  export let selectedFolders;
  export let toggleFolderSelection;
  export let navigateToFolder;
  export let deleteFolderHandler;
  export let selectedFiles;
  export let toggleFileSelection;
  export let editingFileId;
  export let newFileName;
  export let saveFileName;
  export let cancelEditing;
  export let canPreview;
  export let openPreview;
  export let startEditingFile;
  export let downloadFileHandler;
  export let handleDeleteFile;
</script>

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
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
          >Nombre</th
        >
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
          >Tamaño</th
        >
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
          >Modificado</th
        >
        <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider"
          >Acciones</th
        >
      </tr>
    </thead>
    <tbody class="bg-white divide-y divide-gray-200">
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
          <td class="px-6 py-4 whitespace-nowrap">
            <button
              type="button"
              class="flex items-center w-full text-left hover:text-blue-600 transition-colors"
              on:click={() => navigateToFolder(folder._id)}
              aria-label="Abrir carpeta {folder.name}"
            >
              <span class="text-2xl mr-3">📁</span>
              <span class="text-sm font-medium text-gray-900">{folder.name}</span>
            </button>
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">—</td>
          <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500"
            >{formatDate(folder.created_date)}</td
          >
          <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
            <button
              on:click={() => deleteFolderHandler(folder._id)}
              class="text-red-600 hover:text-red-900 ml-4"
            >
              🗑️ Eliminar
            </button>
          </td>
        </tr>
      {/each}

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
          <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{formatBytes(file.size)}</td
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
              on:click={() => downloadFileHandler(file._id, file.filename)}
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
