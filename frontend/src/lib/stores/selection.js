import { writable } from 'svelte/store';

export const selectedFiles = writable(new Set());
export const selectedFolders = writable(new Set());
export const selectAll = writable(false);
export const showBulkActions = writable(false);

export function clearSelections() {
    selectedFiles.set(new Set());
    selectedFolders.set(new Set());
    selectAll.set(false);
    showBulkActions.set(false);
}
