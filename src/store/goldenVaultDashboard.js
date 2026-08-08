import { goldenApiRequest } from './goldenVault.js';

const PREFIX = '/v1/golden-vault/management';

export async function fetchDashboardSummary() {
  return goldenApiRequest(`${PREFIX}/dashboard/summary`);
}

export async function fetchDashboardParticipants({
  limit = 20,
  offset = 0,
  search = '',
  sort = 'joined',
  direction = 'desc',
  status = 'all_current',
  participantType = 'all',
} = {}) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
    sort,
    direction,
    status,
    participant_type: participantType,
  });
  if (search.trim()) params.set('search', search.trim());
  return goldenApiRequest(`${PREFIX}/dashboard/participants?${params.toString()}`);
}

export async function fetchDashboardParticipantDetail(publicId) {
  return goldenApiRequest(`${PREFIX}/dashboard/participants/${encodeURIComponent(publicId)}`);
}

export async function fetchParticipantAccountActions(publicId) {
  return goldenApiRequest(`${PREFIX}/dashboard/participants/${encodeURIComponent(publicId)}/account-actions`);
}

export async function suspendParticipantAccount(publicId, { duration, reason }) {
  return goldenApiRequest(`${PREFIX}/dashboard/participants/${encodeURIComponent(publicId)}/suspend`, {
    method: 'POST',
    body: { duration, reason },
  });
}

export async function unsuspendParticipantAccount(publicId, { reason }) {
  return goldenApiRequest(`${PREFIX}/dashboard/participants/${encodeURIComponent(publicId)}/unsuspend`, {
    method: 'POST',
    body: { reason },
  });
}

export async function resetParticipantPin(publicId) {
  return goldenApiRequest(`${PREFIX}/dashboard/participants/${encodeURIComponent(publicId)}/reset-pin`, {
    method: 'POST',
    body: {},
  });
}

export async function disableParticipantAccount(publicId, { reason }) {
  return goldenApiRequest(`${PREFIX}/dashboard/participants/${encodeURIComponent(publicId)}/disable`, {
    method: 'POST',
    body: { reason },
  });
}

export async function enableParticipantAccount(publicId, { reason }) {
  return goldenApiRequest(`${PREFIX}/dashboard/participants/${encodeURIComponent(publicId)}/enable`, {
    method: 'POST',
    body: { reason },
  });
}

export async function removeParticipantAccount(publicId, { reason, confirmationPublicId }) {
  return goldenApiRequest(`${PREFIX}/dashboard/participants/${encodeURIComponent(publicId)}/remove-account`, {
    method: 'POST',
    body: { reason, confirmation_public_id: confirmationPublicId },
  });
}

export async function sendParticipantMessage(publicId, { subject, body }) {
  return goldenApiRequest(`${PREFIX}/dashboard/participants/${encodeURIComponent(publicId)}/messages`, {
    method: 'POST',
    body: { subject, body },
  });
}

export async function fetchParticipantMessages(publicId, { limit = 20, offset = 0 } = {}) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  return goldenApiRequest(`${PREFIX}/dashboard/participants/${encodeURIComponent(publicId)}/messages?${params.toString()}`);
}

export async function releaseParticipantFeedback(publicId) {
  return goldenApiRequest(`${PREFIX}/participants/${encodeURIComponent(publicId)}/feedback/release`, {
    method: 'POST',
    body: {},
  });
}

export async function refreshParticipantFeedback(publicId) {
  return goldenApiRequest(`${PREFIX}/participants/${encodeURIComponent(publicId)}/feedback/refresh`, {
    method: 'POST',
    body: {},
  });
}

export async function revokeParticipantFeedback(publicId) {
  return goldenApiRequest(`${PREFIX}/participants/${encodeURIComponent(publicId)}/feedback/revoke`, {
    method: 'POST',
    body: {},
  });
}

export async function bulkReleaseFeedback(payload) {
  return goldenApiRequest(`${PREFIX}/participants/feedback/release-bulk`, { method: 'POST', body: payload });
}

export async function bulkRevokeFeedback(payload) {
  return goldenApiRequest(`${PREFIX}/participants/feedback/revoke-bulk`, { method: 'POST', body: payload });
}

export async function bulkRefreshFeedback(payload) {
  return goldenApiRequest(`${PREFIX}/participants/feedback/refresh-bulk`, { method: 'POST', body: payload });
}

export async function bulkMessageParticipants(payload) {
  return goldenApiRequest(`${PREFIX}/participants/bulk/message`, { method: 'POST', body: payload });
}

export async function bulkEmailParticipants(payload) {
  return goldenApiRequest(`${PREFIX}/participants/bulk/email`, { method: 'POST', body: payload });
}

export async function bulkSuspendParticipants(payload) {
  return goldenApiRequest(`${PREFIX}/participants/bulk/suspend`, { method: 'POST', body: payload });
}

export async function bulkReactivateParticipants(payload) {
  return goldenApiRequest(`${PREFIX}/participants/bulk/reactivate`, { method: 'POST', body: payload });
}

export async function bulkRemoveParticipants(payload) {
  return goldenApiRequest(`${PREFIX}/participants/bulk/remove`, { method: 'POST', body: payload });
}

export function buildBulkSelectionPayload({
  selectionMode,
  selectedIds,
  excludedIds,
  filters,
} = {}) {
  if (selectionMode === 'all_matching') {
    const payload = {
      selection_mode: 'all_matching',
      filters: {
        search: filters?.search ?? '',
        sort: filters?.sort ?? 'joined',
        direction: filters?.direction ?? 'desc',
        status: filters?.status ?? 'all_current',
        participantType: filters?.participantType ?? 'all',
      },
    };
    if (excludedIds?.length) payload.excluded_public_ids = excludedIds;
    return payload;
  }
  return {
    participant_public_ids: selectedIds ?? [],
  };
}

export async function fetchGroqProviderStatus() {
  return goldenApiRequest('/v1/research/feedback/provider-status');
}

export async function fetchConsentPdf(consentId) {
  const token = (await import('./goldenVault.js')).getGoldenVaultToken();
  const BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');
  const response = await fetch(`${BASE_URL}${PREFIX}/consents/${consentId}/pdf`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) throw new Error('Unable to open the consent PDF.');
  const blob = await response.blob();
  const disposition = response.headers.get('Content-Disposition') || '';
  const match = disposition.match(/filename="([^"]+)"/);
  return { blob, contentType: response.headers.get('Content-Type'), filename: match?.[1] };
}

export async function downloadConsent(consentId) {
  const token = (await import('./goldenVault.js')).getGoldenVaultToken();
  const BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');
  const response = await fetch(`${BASE_URL}${PREFIX}/consents/${consentId}/download`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) throw new Error('Unable to download the consent PDF.');
  const blob = await response.blob();
  const disposition = response.headers.get('Content-Disposition') || '';
  const match = disposition.match(/filename="([^"]+)"/);
  return { blob, contentType: response.headers.get('Content-Type'), filename: match?.[1] };
}
