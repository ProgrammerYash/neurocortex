import { getToken } from './auth.js';

const BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.errorCode = detail && typeof detail === 'object' && detail.error_code
      ? detail.error_code
      : null;
  }
}

export function getApiBaseUrl() {
  return BASE_URL;
}

export async function apiRequest(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (error) {
    throw new ApiError(
      'Unable to reach the NeuroCortex server. Check that the backend is running.',
      0,
      error.message,
    );
  }

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
    let message = typeof detail === 'string'
      ? detail
      : detail && typeof detail === 'object' && detail.message
        ? detail.message
      : Array.isArray(detail)
        ? detail.map((item) => item.msg || JSON.stringify(item)).join('; ')
        : detail
          ? JSON.stringify(detail)
          : response.statusText || 'Request failed';
    if (detail && typeof detail === 'object' && detail.error_code === 'ACCOUNT_SUSPENDED' && detail.suspended_until) {
      try {
        message = `Your account is temporarily suspended until ${new Date(detail.suspended_until).toLocaleString('en-US', { timeZone: 'America/New_York' })}.`;
      } catch {
        // keep server message
      }
    }
    throw new ApiError(message, response.status, detail);
  }

  return data;
}

export function safeFilename(contentDisposition, fallback = 'download') {
  const utf = contentDisposition?.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
  const plain = contentDisposition?.match(/filename="?([^";]+)"?/i)?.[1];
  let value = fallback;
  try { value = decodeURIComponent(utf || plain || fallback); } catch { value = plain || fallback; }
  return value.replace(/[<>:"/\\|?*\u0000-\u001f]/g, '_').replace(/^\.+/, '') || fallback;
}

export async function apiBlobRequest(path, { method = 'GET', auth = true } = {}) {
  const headers = {};
  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, { method, headers });
  } catch (error) {
    throw new ApiError('Unable to reach the NeuroCortex server. Check that the backend is running.', 0, error.message);
  }
  if (!response.ok) {
    let detail;
    try { detail = await response.json(); } catch { detail = response.statusText; }
    throw new ApiError(typeof detail?.detail === 'string' ? detail.detail : response.statusText || 'Download failed', response.status, detail);
  }
  return {
    blob: await response.blob(),
    filename: safeFilename(response.headers.get('content-disposition'), 'download'),
  };
}
