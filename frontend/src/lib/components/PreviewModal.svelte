<script>
  import { showPreview, previewFile, previewContent, previewError } from '$lib/stores/ui.js';
  import { getFileIcon, formatBytes, formatDate } from '$lib/utils/formatters.js';

  export let closePreview;
  export let downloadFileHandler;
</script>

{#if $showPreview}
  <div
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 preview-modal"
    on:click={closePreview}
    on:keydown={(e) => {
      if (e.key === 'Escape') closePreview();
    }}
    role="button"
    tabindex="0"
    aria-label="Cerrar modal de preview (presiona Escape o clica fuera del contenido)"
  >
    <div
      class="bg-white rounded-lg shadow-xl max-w-4xl max-h-[90vh] w-full mx-4 overflow-hidden preview-modal-content"
      role="dialog"
      aria-modal="true"
      aria-labelledby="preview-title"
    >
      <div class="flex items-center justify-between p-4 border-b border-gray-200">
        <div class="flex items-center space-x-3">
          <span class="text-2xl">{$previewFile ? getFileIcon($previewFile.file_type) : '📄'}</span>
          <div>
            <h3 class="text-lg font-semibold text-gray-900">
              {$previewFile?.filename || 'Preview'}
            </h3>
            <p class="text-sm text-gray-500">
              {$previewFile ? formatBytes($previewFile.size) : ''}
            </p>
          </div>
        </div>
        <button
          type="button"
          on:click={closePreview}
          class="text-gray-400 hover:text-gray-600 text-2xl font-bold"
          aria-label="Cerrar modal"
        >
          ✕
        </button>
      </div>

      <div class="p-4 overflow-auto max-h-[calc(90vh-120px)]">
        {#if $previewError}
          <div class="text-center py-8">
            <div class="text-4xl mb-4">⚠️</div>
            <p class="text-red-600">{$previewError}</p>
          </div>
        {:else if $previewFile}
          {#if $previewFile.file_type.startsWith('image/')}
            <div class="text-center">
              <img
                src={$previewContent}
                alt={$previewFile.filename}
                class="max-w-full max-h-[70vh] object-contain mx-auto rounded"
                on:error={() => previewError.set('Error al cargar la imagen')}
              />
            </div>
          {:else if $previewFile.file_type === 'application/pdf'}
            <div class="w-full h-[70vh]">
              <iframe
                src={$previewContent}
                class="w-full h-full border-0 rounded"
                title="PDF Preview"
              ></iframe>
            </div>
          {:else if $previewFile.file_type.startsWith('text/') || $previewFile.file_type.includes('json') || $previewFile.file_type.includes('javascript')}
            <div class="bg-gray-50 rounded-lg p-4">
              <pre
                class="text-sm text-gray-800 whitespace-pre-wrap overflow-auto max-h-[60vh] font-mono">{$previewContent}</pre>
            </div>
          {:else}
            <div class="text-center py-8">
              <div class="text-4xl mb-4">📄</div>
              <p class="text-gray-600">Este tipo de archivo no se puede previsualizar</p>
              <button
                on:click={() => downloadFileHandler($previewFile._id, $previewFile.filename)}
                class="inline-block mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                ⬇️ Descargar archivo
              </button>
            </div>
          {/if}
        {/if}
      </div>

      <div class="flex items-center justify-between p-4 border-t border-gray-200 bg-gray-50">
        <div class="text-sm text-gray-600">
          {#if $previewFile}
            Tipo: {$previewFile.file_type} • Subido: {formatDate($previewFile.upload_date)}
          {/if}
        </div>
        <div class="flex space-x-2">
          <button
            on:click={() => downloadFileHandler($previewFile?._id, $previewFile?.filename)}
            class="px-3 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition-colors"
          >
            ⬇️ Descargar
          </button>
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
