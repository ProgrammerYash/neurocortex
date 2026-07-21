import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { apiBlob, ApiError } from './apiClient.js';

vi.mock('./auth.js', () => ({
  getToken: vi.fn(() => 'test-token'),
}));

function mockFetchResponse({
  ok = true,
  status = 200,
  headers = {},
  body = '%PDF-1.4',
  blobFactory,
} = {}) {
  const headerMap = new Map(
    Object.entries(headers).map(([key, value]) => [key.toLowerCase(), value]),
  );
  const blob = blobFactory
    ? blobFactory()
    : new Blob([body], { type: headers['Content-Type']?.split(';')[0] || 'application/pdf' });
  return {
    ok,
    status,
    statusText: ok ? 'OK' : 'Bad Request',
    headers: {
      get(name) {
        return headerMap.get(String(name).toLowerCase()) ?? null;
      },
    },
    json: vi.fn(async () => JSON.parse(typeof body === 'string' ? body : '{}')),
    text: vi.fn(async () => (typeof body === 'string' ? body : '')),
    blob: vi.fn(async () => blob),
  };
}

describe('apiBlob', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('returns a real Blob with filename and contentType', async () => {
    fetch.mockResolvedValue(mockFetchResponse({
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'inline; filename="NC-ABC123-consent.pdf"',
      },
    }));

    const result = await apiBlob('/v1/researcher/consents/test/pdf');
    expect(result.blob).toBeInstanceOf(Blob);
    expect(result.blob.size).toBeGreaterThan(0);
    expect(result.contentType).toContain('application/pdf');
    expect(result.filename).toBe('NC-ABC123-consent.pdf');
  });

  it('never returns a fetch Response wrapper for createObjectURL callers', async () => {
    const response = mockFetchResponse();
    fetch.mockResolvedValue(response);
    const result = await apiBlob('/file');
    expect(result).toEqual(expect.objectContaining({ blob: expect.any(Blob) }));
    expect(result.blob).toBeInstanceOf(Blob);
    expect(result).not.toBeInstanceOf(Blob);
  });

  it('throws on JSON error responses without producing a Blob', async () => {
    fetch.mockResolvedValue(mockFetchResponse({
      ok: false,
      status: 403,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ detail: 'Forbidden' }),
    }));

    await expect(apiBlob('/v1/researcher/consents/download-all')).rejects.toBeInstanceOf(ApiError);
    expect(fetch.mock.results[0]).toBeDefined();
  });

  it('throws when the Blob is empty', async () => {
    fetch.mockResolvedValue(mockFetchResponse({
      blobFactory: () => new Blob([], { type: 'application/pdf' }),
    }));

    await expect(apiBlob('/empty')).rejects.toMatchObject({
      message: 'The downloaded file was empty.',
    });
  });

  it('uses filename fallback when Content-Disposition is missing', async () => {
    fetch.mockResolvedValue(mockFetchResponse({
      headers: { 'Content-Type': 'application/zip' },
    }));

    const result = await apiBlob('/zip', { filenameFallback: 'neurocortex-consents.zip' });
    expect(result.filename).toBe('neurocortex-consents.zip');
  });
});

describe('consent download createObjectURL contract', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:test');
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('passes expect.any(Blob) to createObjectURL for PDF and ZIP payloads', async () => {
    fetch
      .mockResolvedValueOnce(mockFetchResponse({
        headers: {
          'Content-Type': 'application/pdf',
          'Content-Disposition': 'attachment; filename="NC-TEST-consent.pdf"',
        },
      }))
      .mockResolvedValueOnce(mockFetchResponse({
        headers: {
          'Content-Type': 'application/zip',
          'Content-Disposition': 'attachment; filename="neurocortex-consents.zip"',
        },
        body: 'PK',
      }));

    const pdf = await apiBlob('/pdf');
    URL.createObjectURL(pdf.blob);
    expect(URL.createObjectURL).toHaveBeenCalledWith(expect.any(Blob));

    const zip = await apiBlob('/zip');
    URL.createObjectURL(zip.blob);
    expect(URL.createObjectURL).toHaveBeenLastCalledWith(expect.any(Blob));
  });

  it('does not call createObjectURL for failed JSON responses', async () => {
    fetch.mockResolvedValue(mockFetchResponse({
      ok: false,
      status: 500,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ detail: 'Consent archive could not be generated' }),
    }));

    await expect(apiBlob('/zip')).rejects.toThrow();
    expect(URL.createObjectURL).not.toHaveBeenCalled();
  });
});
