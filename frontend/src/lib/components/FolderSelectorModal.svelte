<script>
  import {
    showFolderSelector,
    allFolders,
    selectorCurrentFolder,
    selectedTargetFolder,
    selectorMode,
  } from '$lib/stores/ui.js';
  import { selectedFiles, selectedFolders } from '$lib/stores/selection.js';
  import { formatDate } from '$lib/utils/formatters.js';
  export let closeFolderSelector;
  export let navigateToFolderInSelector;
  export let selectTargetFolder;
  export let confirmAction;
  function handleOverlayClick(e) {
    if (e.target === e.currentTarget) {
      closeFolderSelector();
    }
  }
</script>

{#if $showFolderSelector}
  <div
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    on:click={handleOverlayClick}
    on:keydown={(e) => {
      if (e.key === 'Escape') closeFolderSelector();
    }}
    role="button"
    tabindex="0"
    aria-label="Cerrar modal selector de carpetas (presiona Escape o clica fuera del contenido)"
  >
    <div
      class="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden"
      role="dialog"
      aria-modal="true"
      aria-labelledby="selector-title"
    >
      <div class="flex items-center justify-between p-4 border-b border-gray-200">
        <div class="flex items-center space-x-3">
          <span class="text-2xl">{$selectorMode === 'move' ? '📁' : '📋'}</span>
          <div>
            <h3 id="selector-title" class="text-lg font-semibold text-gray-900">
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
      <div class="p-4 overflow-y-auto max-h-[50vh]">
        <button
          type="button"
          class="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-100 cursor-pointer border-2 transition-colors w-full text-left {$selectedTargetFolder ===
          null
            ? 'border-blue-500 bg-blue-50'
            : 'border-transparent'}"
          on:click={() => selectTargetFolder(null)}
          aria-label="Seleccionar carpeta raíz como destino"
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
        </button>
        {#each $allFolders as folder}
          <button
            type="button"
            class="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-100 cursor-pointer border-2 transition-colors w-full text-left {$selectedTargetFolder?._id ===
            folder._id
              ? 'border-blue-500 bg-blue-50'
              : 'border-transparent'}"
            on:click={() => selectTargetFolder(folder)}
            aria-label="Seleccionar carpeta {folder.name} como destino"
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
                aria-label="Explorar subcarpetas de {folder.name}"
              >
                ➡️
              </button>
            </div>
          </button>
        {/each}
        {#if $allFolders.length === 0}
          <div class="text-center py-8 text-gray-500">
            <div class="text-4xl mb-2">📂</div>
            <p>No hay carpetas disponibles en esta ubicación</p>
          </div>
        {/if}
      </div>
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
