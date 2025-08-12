import { writable } from 'svelte/store';

export const isLoading = writable(true);
export const errorMessage = writable('');
export const successMessage = writable('');
export const uploadProgress = writable(null);
export const viewMode = writable('list'); // 'list' or 'grid'
export const showCreateFolder = writable(false);

// Preview Modal
export const showPreview = writable(false);
export const previewFile = writable(null);
export const previewContent = writable('');
export const previewError = writable('');

// Folder Selector Modal
export const showFolderSelector = writable(false);
export const allFolders = writable([]);
export const selectorCurrentFolder = writable('root');
export const selectedTargetFolder = writable(null);
export const selectorMode = writable('move'); // 'move' o 'copy'
