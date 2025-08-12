<script>
  import {
    authMode,
    authUsername,
    authPassword,
    authError,
    authLoading,
  } from '$lib/stores/auth.js';

  export let handleAuthSubmit;
  export let handleKeyPress;
</script>

<main
  class="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-blue-100 p-4"
>
  <div class="bg-white w-full max-w-md rounded-2xl shadow-lg p-8 space-y-6">
    <h1 class="text-2xl font-bold text-center text-gray-800">
      {$authMode === 'login' ? 'Iniciar Sesión' : 'Crear Cuenta'}
    </h1>
    <p class="text-center text-sm text-gray-500">
      Accede a tu Drive. Usuario admin por defecto: admin / admin123
    </p>
    {#if $authError}
      <div class="bg-red-100 text-red-700 text-sm px-4 py-2 rounded">{$authError}</div>
    {/if}
    <form on:submit|preventDefault={handleAuthSubmit} class="space-y-4">
      <div>
        <label for="username" class="block text-sm font-medium text-gray-700 mb-1">Usuario</label>
        <input
          id="username"
          type="text"
          bind:value={$authUsername}
          on:keydown={handleKeyPress}
          class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          placeholder="usuario"
          disabled={$authLoading}
        />
      </div>
      <div>
        <label for="password" class="block text-sm font-medium text-gray-700 mb-1">Contraseña</label
        >
        <input
          id="password"
          type="password"
          bind:value={$authPassword}
          on:keydown={handleKeyPress}
          class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          placeholder="••••••••"
          disabled={$authLoading}
        />
      </div>
      <button
        type="submit"
        class="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 rounded-lg transition-colors disabled:opacity-50"
        disabled={$authLoading}
      >
        {#if $authLoading}
          <div class="flex items-center justify-center space-x-2">
            <div
              class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"
            ></div>
            <span>Cargando...</span>
          </div>
        {:else}
          {$authMode === 'login' ? 'Entrar' : 'Registrarme'}
        {/if}
      </button>
    </form>
    <div class="text-center text-sm text-gray-600">
      {#if $authMode === 'login'}
        ¿No tienes cuenta? <button
          class="text-blue-600 hover:underline"
          on:click={() => {
            $authMode = 'register';
            $authError = '';
          }}>Registrarme</button
        >
      {:else}
        ¿Ya tienes cuenta? <button
          class="text-blue-600 hover:underline"
          on:click={() => {
            $authMode = 'login';
            $authError = '';
          }}>Entrar</button
        >
      {/if}
    </div>
  </div>
</main>
