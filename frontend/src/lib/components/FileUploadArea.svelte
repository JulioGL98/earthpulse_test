<script>
  export let isDropping;
  export let handleDragEnter;
  export let handleDragLeave;
  export let handleDrop;
  export let handleFileUpload;
</script>

<div
  class="bg-white p-6 rounded-lg shadow-sm mb-6 border-2 border-dashed transition-all duration-300 {isDropping
    ? 'border-blue-500 bg-blue-50'
    : 'border-gray-300'}"
  role="button"
  tabindex="0"
  aria-label="Área de carga de archivos. Arrastra archivos aquí o presiona Enter para seleccionar archivos"
  aria-describedby="upload-instructions"
  on:dragenter={handleDragEnter}
  on:dragleave={handleDragLeave}
  on:dragover|preventDefault
  on:drop={handleDrop}
  on:keydown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      document.getElementById('file-upload').click();
    }
  }}
>
  <div class="text-center">
    <div class="text-4xl mb-4">📤</div>
    <h3 class="text-lg font-medium text-gray-900 mb-2">Subir archivos</h3>
    <p id="upload-instructions" class="text-gray-600 mb-4">
      Arrastra archivos aquí o selecciona desde tu computadora
    </p>
    <label
      for="file-upload"
      class="inline-flex items-center px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 cursor-pointer transition-colors"
    >
      📎 Seleccionar Archivos
    </label>
    <input id="file-upload" type="file" class="hidden" on:change={handleFileUpload} multiple />
  </div>
</div>
