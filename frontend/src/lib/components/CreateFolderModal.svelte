<script>
  import { showCreateFolder } from '$lib/stores/ui.js';
  export let newFolderName;
  export let createFolderHandler;
</script>

{#if $showCreateFolder}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-white p-6 rounded-lg shadow-xl max-w-md w-full mx-4">
      <h3 class="text-lg font-medium mb-4">Crear Nueva Carpeta</h3>
      <input
        type="text"
        placeholder="Nombre de la carpeta"
        bind:value={$newFolderName}
        class="w-full px-3 py-2 border border-gray-300 rounded-lg mb-4"
        on:keydown={(e) => e.key === 'Enter' && createFolderHandler()}
      />
      <div class="flex justify-end space-x-3">
        <button
          on:click={() => showCreateFolder.set(false)}
          class="px-4 py-2 text-gray-600 hover:text-gray-800"
        >
          Cancelar
        </button>
        <button
          on:click={createFolderHandler}
          class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          Crear
        </button>
      </div>
    </div>
  </div>
{/if}
