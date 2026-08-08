import { ApiError } from './apiClient.js';

const GOLDEN_TOKEN_KEY = 'nc3_golden_vault_token';
const BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

export function getGoldenVaultToken() {
  try {
    return localStorage.getItem(GOLDEN_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setGoldenVaultToken(token) {
  try {
    localStorage.setItem(GOLDEN_TOKEN_KEY, token);
  } catch (error) {
    console.warn('Golden Vault token save failed:', error);
  }
}

export function clearGoldenVaultToken() {
  try {
    localStorage.removeItem(GOLDEN_TOKEN_KEY);
  } catch (error) {
    console.warn('Golden Vault token clear failed:', error);
  }
}

export function isGoldenVaultAuthed() {
  const token = getGoldenVaultToken();
  if (!token) return false;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    if (payload.role !== 'golden_vault') return false;
    if (payload.exp && payload.exp * 1000 < Date.now()) return false;
    return true;
  } catch {
    return false;
  }
}

export async function goldenApiRequest(path, { method = 'GET', body, auth = true, signal } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth) {
    const token = getGoldenVaultToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    signal,
  });
  let data = null;
  const text = await response.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }
  if (!response.ok) {
    const detail = data?.detail;
    const message = typeof detail === 'string'
      ? detail
      : detail?.message || response.statusText || 'Request failed';
    throw new ApiError(message, response.status, detail);
  }
  return data;
}

export async function loginGoldenVaultWithApi({ code }) {
  const data = await goldenApiRequest('/v1/golden-vault/login', {
    method: 'POST',
    auth: false,
    body: { code },
  });
  setGoldenVaultToken(data.access_token);
  return data;
}

export async function fetchGoldenVaultParticipants(params = {}, options = {}) {
  const qs = new URLSearchParams({
    limit: String(params.limit ?? 25),
    offset: String(params.offset ?? 0),
  });
  if (params.search?.trim()) qs.set('search', params.search.trim());
  if (params.goldenEnabled) qs.set('golden_enabled', params.goldenEnabled);
  if (params.feedbackFilter) qs.set('feedback_filter', params.feedbackFilter);
  if (params.syntheticBatchId) qs.set('synthetic_batch_id', params.syntheticBatchId);
  if (params.participantType && params.participantType !== 'all') {
    qs.set('participant_type', params.participantType);
  }
  return goldenApiRequest(`/v1/golden-vault/participants?${qs.toString()}`, { signal: options.signal });
}

export async function goldenVaultPatchAutoSession(publicId, enabled) {
  return goldenApiRequest(`/v1/golden-vault/participants/${encodeURIComponent(publicId)}/auto-session`, {
    method: 'PATCH',
    body: { enabled },
  });
}

export async function goldenVaultRescheduleAutoSession(publicId) {
  return goldenApiRequest(`/v1/golden-vault/participants/${encodeURIComponent(publicId)}/auto-session/reschedule`, {
    method: 'POST',
  });
}

export async function goldenVaultRunAutoSessionNow(publicId) {
  return goldenApiRequest(`/v1/golden-vault/participants/${encodeURIComponent(publicId)}/auto-session/run-now`, {
    method: 'POST',
  });
}

export async function goldenVaultBulk(payload) {
  return goldenApiRequest('/v1/golden-vault/participants/bulk', {
    method: 'POST',
    body: payload,
  });
}

export async function goldenVaultPatchParticipant(publicId, body) {
  return goldenApiRequest(`/v1/golden-vault/participants/${encodeURIComponent(publicId)}`, {
    method: 'PATCH',
    body,
  });
}

export async function goldenVaultAddSessions(publicId, amount) {
  return goldenApiRequest(`/v1/golden-vault/participants/${encodeURIComponent(publicId)}/sessions/add`, {
    method: 'POST',
    body: { amount },
  });
}

export async function goldenVaultDeleteSessions(publicId, amount) {
  return goldenApiRequest(`/v1/golden-vault/participants/${encodeURIComponent(publicId)}/sessions/delete`, {
    method: 'POST',
    body: { amount },
  });
}

export async function goldenVaultAddCoins(publicId, amount) {
  return goldenApiRequest(`/v1/golden-vault/participants/${encodeURIComponent(publicId)}/coins/add`, {
    method: 'POST',
    body: { amount },
  });
}

export async function goldenVaultDeleteCoins(publicId, amount) {
  return goldenApiRequest(`/v1/golden-vault/participants/${encodeURIComponent(publicId)}/coins/delete`, {
    method: 'POST',
    body: { amount },
  });
}

export async function goldenVaultPreviewAutoData(publicId, body) {
  return goldenApiRequest(`/v1/golden-vault/participants/${encodeURIComponent(publicId)}/auto-data/preview`, {
    method: 'POST',
    body,
  });
}

export async function goldenVaultApplyAutoData(publicId, body) {
  return goldenApiRequest(`/v1/golden-vault/participants/${encodeURIComponent(publicId)}/auto-data/apply`, {
    method: 'POST',
    body,
  });
}

export async function goldenVaultPatchAutoData(publicId, body) {
  return goldenApiRequest(`/v1/golden-vault/participants/${encodeURIComponent(publicId)}/auto-data`, {
    method: 'PATCH',
    body,
  });
}

export async function goldenVaultAdjustSessions(publicId, body) {
  return goldenApiRequest(`/v1/golden-vault/participants/${encodeURIComponent(publicId)}/sessions`, {
    method: 'POST',
    body,
  });
}

export async function goldenVaultAdjustCoins(publicId, body) {
  return goldenApiRequest(`/v1/golden-vault/participants/${encodeURIComponent(publicId)}/coins`, {
    method: 'POST',
    body,
  });
}

export async function goldenVaultRegenerateMetrics(publicId) {
  return goldenApiRequest(`/v1/golden-vault/participants/${encodeURIComponent(publicId)}/regenerate-metrics`, {
    method: 'POST',
  });
}

export async function goldenVaultReleaseFeedback(publicId) {
  return goldenApiRequest(`/v1/golden-vault/participants/${encodeURIComponent(publicId)}/feedback/release`, {
    method: 'POST',
  });
}

export async function goldenVaultRevokeFeedback(publicId) {
  return goldenApiRequest(`/v1/golden-vault/participants/${encodeURIComponent(publicId)}/feedback/revoke`, {
    method: 'POST',
  });
}

export async function goldenVaultRegenerateFeedback(publicId) {
  return goldenApiRequest(`/v1/golden-vault/participants/${encodeURIComponent(publicId)}/feedback/regenerate`, {
    method: 'POST',
  });
}

export async function goldenVaultResetParticipant(publicId) {
  return goldenApiRequest(`/v1/golden-vault/participants/${encodeURIComponent(publicId)}/reset`, {
    method: 'POST',
  });
}

export async function fetchGoldenVaultAuditHistory(options = {}) {
  return goldenApiRequest('/v1/golden-vault/audit-history', { signal: options.signal });
}

export function signOutGoldenVault() {
  clearGoldenVaultToken();
}

export async function goldenVaultFakeUsersPreview(body) {
  return goldenApiRequest('/v1/golden-vault/fake-users/preview', { method: 'POST', body });
}

export async function goldenVaultFakeUsersGenerate(body) {
  return goldenApiRequest('/v1/golden-vault/fake-users/generate', { method: 'POST', body });
}

export async function goldenVaultFakeUsersBatchStatus(batchId) {
  return goldenApiRequest(`/v1/golden-vault/fake-users/batches/${encodeURIComponent(batchId)}`);
}

export async function goldenVaultFakeUsersProcessBatch(batchId) {
  return goldenApiRequest(`/v1/golden-vault/fake-users/batches/${encodeURIComponent(batchId)}/process`, {
    method: 'POST',
  });
}

export async function goldenVaultFakeUsersClaimCredentials(batchId) {
  return goldenApiRequest(`/v1/golden-vault/fake-users/batches/${encodeURIComponent(batchId)}/credentials`);
}
