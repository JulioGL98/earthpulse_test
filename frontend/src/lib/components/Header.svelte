<script>
  import { viewMode } from '$lib/stores/ui.js';
  export let logout;
</script>

<header class="mb-8 flex items-center justify-between">
  <div>
    <h1 class="text-4xl font-bold text-gray-900">Mi Drive</h1>
    <p class="text-gray-600 mt-1">Gestiona tus archivos y carpetas de forma sencilla</p>
  </div>
  <div class="flex items-center space-x-4">
    <button class="text-sm text-gray-600 hover:text-red-600" on:click={logout}
      >🔐 Cerrar sesión</button
    >
    <div class="flex border rounded-lg overflow-hidden">
      <button
        class="px-3 py-2 text-sm {$viewMode === 'list'
          ? 'bg-blue-500 text-white'
          : 'bg-white text-gray-700'}"
        on:click={() => viewMode.set('list')}>📋 Lista</button
      >
      <button
        class="px-3 py-2 text-sm {$viewMode === 'grid'
          ? 'bg-blue-500 text-white'
          : 'bg-white text-gray-700'}"
        on:click={() => viewMode.set('grid')}>⊞ Cuadrícula</button
      >
    </div>
  </div>
</header>
