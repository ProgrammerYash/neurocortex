import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from './apiClient.js';
import { clearGoldenVaultToken, goldenApiRequest, setGoldenVaultToken } from './goldenVault.js';
import * as goldenVaultDashboard from './goldenVaultDashboard.js';

function mockJsonResponse({ ok = true, status = 200, body = {} } = {}) {
  const text = JSON.stringify(body);
  return {
    ok,
    status,
    statusText: ok ? 'OK' : 'Forbidden',
    text: async () => text,
  };
}

describe('goldenVaultDashboard store', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
    setGoldenVaultToken('golden-jwt-token');
  });

  afterEach(() => {
    clearGoldenVaultToken();
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('imports successfully with dashboard API helpers', () => {
    expect(typeof goldenVaultDashboard.fetchDashboardSummary).toBe('function');
    expect(typeof goldenVaultDashboard.fetchDashboardParticipants).toBe('function');
    expect(typeof goldenVaultDashboard.buildBulkSelectionPayload).toBe('function');
  });

  it('fetchDashboardSummary uses the shared goldenApiRequest helper with auth headers', async () => {
    fetch.mockResolvedValue(mockJsonResponse({ body: { totalParticipants: 2 } }));

    const result = await goldenVaultDashboard.fetchDashboardSummary();

    expect(fetch).toHaveBeenCalledTimes(1);
    const [url, options] = fetch.mock.calls[0];
    expect(url).toContain('/v1/golden-vault/management/dashboard/summary');
    expect(options.method).toBe('GET');
    expect(options.headers.Authorization).toBe('Bearer golden-jwt-token');
    expect(options.headers['Content-Type']).toBe('application/json');
    expect(result).toEqual({ totalParticipants: 2 });
  });

  it('fetchDashboardParticipants builds query params through goldenApiRequest', async () => {
    fetch.mockResolvedValue(mockJsonResponse({ body: { items: [], total: 0 } }));

    await goldenVaultDashboard.fetchDashboardParticipants({
      search: '  demo  ',
      participantType: 'synthetic_demo',
      status: 'active',
    });

    const [url, options] = fetch.mock.calls[0];
    expect(url).toContain('/v1/golden-vault/management/dashboard/participants?');
    expect(url).toContain('search=demo');
    expect(url).toContain('participant_type=synthetic_demo');
    expect(url).toContain('status=active');
    expect(options.headers.Authorization).toBe('Bearer golden-jwt-token');
  });

  it('throws ApiError for failed dashboard responses', async () => {
    fetch.mockResolvedValue(mockJsonResponse({
      ok: false,
      status: 403,
      body: { detail: 'Forbidden' },
    }));

    const error = await goldenVaultDashboard.fetchDashboardSummary().catch(caught => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      message: 'Forbidden',
      status: 403,
    });
  });
});

describe('goldenApiRequest export', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    clearGoldenVaultToken();
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('sends Golden Vault bearer token when auth is enabled', async () => {
    setGoldenVaultToken('vault-token');
    fetch.mockResolvedValue(mockJsonResponse({ body: { ok: true } }));

    await goldenApiRequest('/v1/golden-vault/management/dashboard/summary');

    const [, options] = fetch.mock.calls[0];
    expect(options.headers.Authorization).toBe('Bearer vault-token');
  });

  it('omits auth header when auth is disabled', async () => {
    setGoldenVaultToken('vault-token');
    fetch.mockResolvedValue(mockJsonResponse({
      body: { access_token: 'new-token', token_type: 'bearer' },
    }));

    await goldenApiRequest('/v1/golden-vault/login', {
      method: 'POST',
      auth: false,
      body: { code: 'secret' },
    });

    const [, options] = fetch.mock.calls[0];
    expect(options.headers.Authorization).toBeUndefined();
    expect(JSON.parse(options.body)).toEqual({ code: 'secret' });
  });
});
