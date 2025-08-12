import { writable } from 'svelte/store';

export const authToken = writable(null);
export const authUser = writable(null);
export const showAuthScreen = writable(true);
export const authMode = writable('login'); // 'login' | 'register'
export const authUsername = writable('');
export const authPassword = writable('');
export const authError = writable('');
export const authLoading = writable(false);

export const API_URL = 'http://localhost:8000';

export function saveToken(token) {
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('auth_token', token);
  }
  authToken.set(token);
}

export function loadToken() {
  if (typeof localStorage !== 'undefined') {
    const t = localStorage.getItem('auth_token');
    if (t) authToken.set(t);
  }
}

export function logout() {
  if (typeof localStorage !== 'undefined') {
    localStorage.removeItem('auth_token');
  }
  authToken.set(null);
  authUser.set(null);
  showAuthScreen.set(true);
  authLoading.set(false);
  authError.set('');
  authUsername.set('');
  authPassword.set('');
}
