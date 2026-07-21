import { apiRequest } from './apiClient.js';

export async function fetchParticipantMessages({ limit = 20, offset = 0, unreadOnly = false } = {}) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
    unread_only: String(unreadOnly),
  });
  return apiRequest(`/v1/participants/me/messages?${params.toString()}`);
}

export async function fetchUnreadMessageCount() {
  return apiRequest('/v1/participants/me/messages/unread-count');
}

export async function markMessageRead(messageId) {
  return apiRequest(`/v1/participants/me/messages/${encodeURIComponent(messageId)}/read`, {
    method: 'POST',
    body: {},
  });
}

export async function sendParticipantMessage(publicId, { subject, body }) {
  return apiRequest(`/v1/research/dashboard/participants/${encodeURIComponent(publicId)}/messages`, {
    method: 'POST',
    body: { subject, body },
  });
}

export async function fetchSentParticipantMessages(publicId, { limit = 20, offset = 0 } = {}) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  return apiRequest(`/v1/research/dashboard/participants/${encodeURIComponent(publicId)}/messages?${params.toString()}`);
}
