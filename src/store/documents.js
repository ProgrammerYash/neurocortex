import { getToken } from './auth.js';
import { getApiBaseUrl } from './apiClient.js';

export async function fetchDocuments() {
  return apiRequest('/v1/research/documents');
}

export async function fetchDocument(documentId) {
  return apiRequest(`/v1/research/documents/${documentId}`);
}

export async function createForm4Draft(body = {}) {
  return apiRequest('/v1/research/documents/form-4/draft', { method: 'POST', body });
}

export async function updateForm4Document(documentId, body) {
  return apiRequest(`/v1/research/documents/form-4/${documentId}`, { method: 'PUT', body });
}

export async function updateDocumentStatus(documentId, body) {
  return apiRequest(`/v1/research/documents/form-4/${documentId}/status`, { method: 'PUT', body });
}

export async function generateForm4Document(documentId) {
  return apiRequest(`/v1/research/documents/form-4/${documentId}/generate`, { method: 'POST' });
}

export function getDocumentDownloadUrl(documentId) {
  return `${getApiBaseUrl()}/v1/research/documents/${documentId}/download`;
}

export async function downloadDocument(documentId) {
  const token = getToken();
  const response = await fetch(getDocumentDownloadUrl(documentId), {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) throw new Error('Document download failed');
  return response.blob();
}
