<script>
  import { searchTerm } from '$lib/stores/fileManager.js';
  import { showCreateFolder, viewMode } from '$lib/stores/ui.js';
  import {
    selectedFiles,
    selectedFolders,
    showBulkActions,
    clearSelections,
  } from '$lib/stores/selection.js';

  export let deleteSelectedItems;
  export let moveSelectedItems;
  export let copySelectedItems;
  export let sortBy;
  export let sortOrder;
</script>

<div class="bg-white rounded-lg shadow-sm p-4 mb-6">
  <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0">
    <div class="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-4 items-center">
      <div class="relative">
        <input
          type="text"
          placeholder="Buscar archivos..."
          bind:value={$searchTerm}
          class="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <div class="absolute left-3 top-2.5 text-gray-400">🔍</div>
      </div>

      <button
        on:click={() => showCreateFolder.set(true)}
        class="flex items-center px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
      >
        📁 Nueva Carpeta
      </button>

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

    <div class="flex items-center space-x-2">
      <label for="sort-by" class="text-sm text-gray-600">Ordenar por:</label>
      <select
        id="sort-by"
        bind:value={$sortBy}
        class="px-3 py-1 border border-gray-300 rounded text-sm"
      >
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
