import { apiRequest } from './apiClient.js';

export async function fetchAllSessions() {
  const data = await apiRequest('/v1/participants/me/sessions');
  return Array.isArray(data) ? data : [];
}

export async function fetchTodaySession() {
  return apiRequest('/v1/participants/me/sessions/today');
}

export async function upsertModuleResult(sessionDate, moduleKey, payload) {
  return apiRequest(
    `/v1/participants/me/sessions/${sessionDate}/modules/${moduleKey}`,
    {
      method: 'PUT',
      body: { payload },
    },
  );
}
