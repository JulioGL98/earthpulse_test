<script>
  import { isLoading, successMessage, errorMessage, uploadProgress } from '$lib/stores/ui.js';
</script>

<div class="fixed bottom-4 right-4 z-50 flex flex-col space-y-3">
  {#if $isLoading}
    <div class="loading-popup">
      {#if $uploadProgress}
        <div class="bg-blue-500 text-white px-5 py-4 rounded-lg shadow-lg upload-popup">
          <div class="flex items-center space-x-3 mb-3">
            <div class="text-xl">📤</div>
            <span class="font-semibold">Subiendo archivo</span>
          </div>
          <div class="text-sm opacity-90 mb-3">
            <div class="truncate font-medium mb-1">{$uploadProgress.fileName}</div>
            <div class="text-xs opacity-75">
              Archivo {$uploadProgress.currentFile} de {$uploadProgress.totalFiles}
            </div>
          </div>
          <div class="upload-progress-container mb-3">
            <div class="w-full bg-blue-700 rounded-full h-2.5 overflow-hidden">
              <div
                class="upload-progress-bar h-2.5 rounded-full progress-bar"
                style="width: {$uploadProgress.progress}%"
              ></div>
            </div>
          </div>
          <div class="flex justify-between items-center text-sm">
            <span class="opacity-75">Progreso</span>
            <span class="font-bold text-blue-100">{$uploadProgress.progress}%</span>
          </div>
        </div>
      {:else}
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

  {#if $errorMessage}
    <div class="error-popup">
      <div class="bg-red-500 text-white px-4 py-3 rounded-lg shadow-lg flex items-center space-x-3">
        <div class="text-lg">❌</div>
        <span class="font-medium">{$errorMessage}</span>
      </div>
    </div>
  {/if}
</div>

<style>
  .loading-popup,
  .success-popup,
  .error-popup {
    animation: slideInFromRight 0.3s ease-out;
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
</style>
