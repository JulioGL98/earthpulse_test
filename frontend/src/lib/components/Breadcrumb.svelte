<script>
  import { folderPath, currentFolder, currentFolderInfo } from '$lib/stores/fileManager.js';
  export let navigateToFolder;
  export let navigateBack;
</script>

<nav class="mb-6">
  <div class="flex items-center justify-between">
    <div class="flex items-center space-x-2 text-sm text-gray-600">
      <button class="hover:text-blue-600 hover:underline" on:click={() => navigateToFolder('root')}>
        🏠 Inicio
      </button>
      {#if $folderPath !== '/'}
        <span>/</span>
        <span class="text-gray-900 font-medium">{$folderPath}</span>
      {/if}
    </div>

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
