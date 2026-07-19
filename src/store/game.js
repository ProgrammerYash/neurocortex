import { apiRequest } from './apiClient.js';

export async function fetchGameData() {
  const data = await apiRequest('/v1/participants/me/game');
  return data ?? null;
}

export async function saveGameData(gameData) {
  return apiRequest('/v1/participants/me/game', {
    method: 'PUT',
    body: gameData,
  });
}
