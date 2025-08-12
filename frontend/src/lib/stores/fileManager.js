import { writable } from 'svelte/store';

export const files = writable([]);
export const folders = writable([]);
export const currentFolder = writable('root');
export const folderPath = writable('/');
export const folderHistory = writable([]);
export const currentFolderInfo = writable(null);
export const searchTerm = writable('');
