import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ParticipantConsentSection from './ParticipantConsentSection.jsx';
import ParticipantsSection from './ParticipantsSection.jsx';
import { downloadConsent, downloadAllConsents, fetchConsentPdf } from '../../store/consent.js';
import { fetchDashboardParticipants, fetchDashboardParticipantDetail, fetchParticipantAccountActions } from '../../store/research.js';

vi.mock('../../store/consent.js', () => ({
  fetchConsentPdf: vi.fn(),
  downloadConsent: vi.fn(),
  downloadAllConsents: vi.fn(),
}));

vi.mock('../../store/research.js', () => ({
  fetchDashboardParticipants: vi.fn(),
  fetchDashboardParticipantDetail: vi.fn(),
  fetchParticipantAccountActions: vi.fn(),
}));

const pdfPayload = {
  blob: new Blob(['%PDF'], { type: 'application/pdf' }),
  filename: 'NC-TEST-1-consent.pdf',
  contentType: 'application/pdf',
};

const zipPayload = {
  blob: new Blob(['PK'], { type: 'application/zip' }),
  filename: 'neurocortex-consents.zip',
  contentType: 'application/zip',
};

const recordedDetail = {
  participantId: 'NC-TEST-1',
  consentRecorded: true,
  consentRecordId: 'consent-1',
  consentVersion: 'v1',
  consentStudentSignedDisplay: 'Jul 20, 2026 10:00 PM',
  consentGuardianSignedDisplay: 'Jul 20, 2026 10:01 PM',
};

describe('ParticipantConsentSection downloads', () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  beforeEach(() => {
    fetchConsentPdf.mockResolvedValue(pdfPayload);
    downloadConsent.mockResolvedValue(pdfPayload);
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:consent');
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
  });

  it('passes a real Blob to createObjectURL when viewing PDF', async () => {
    const tab = { location: { href: '' }, close: vi.fn() };
    vi.spyOn(window, 'open').mockReturnValue(tab);
    render(<ParticipantConsentSection detail={recordedDetail} showToast={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'View PDF' }));
    await waitFor(() => expect(fetchConsentPdf).toHaveBeenCalledWith('consent-1'));
    expect(URL.createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
    expect(tab.location.href).toBe('blob:consent');
  });

  it('passes a real Blob to createObjectURL when downloading PDF', async () => {
    render(<ParticipantConsentSection detail={recordedDetail} showToast={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Download PDF' }));
    await waitFor(() => expect(downloadConsent).toHaveBeenCalledWith('consent-1'));
    expect(URL.createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
    await waitFor(() => expect(URL.revokeObjectURL).toHaveBeenCalled(), { timeout: 2000 });
  });

  it('shows popup-blocked error without calling createObjectURL', async () => {
    vi.spyOn(window, 'open').mockReturnValue(null);
    render(<ParticipantConsentSection detail={recordedDetail} showToast={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'View PDF' }));
    expect(await screen.findByText(/blocked the PDF tab/i)).toBeInTheDocument();
    expect(fetchConsentPdf).not.toHaveBeenCalled();
    expect(URL.createObjectURL).not.toHaveBeenCalled();
  });

  it('closes blank tab and shows safe error when view fails', async () => {
    const tab = { location: { href: '' }, close: vi.fn() };
    vi.spyOn(window, 'open').mockReturnValue(tab);
    fetchConsentPdf.mockRejectedValue(new Error('network'));
    const showToast = vi.fn();
    render(<ParticipantConsentSection detail={recordedDetail} showToast={showToast} />);
    fireEvent.click(screen.getByRole('button', { name: 'View PDF' }));
    await waitFor(() => expect(showToast).toHaveBeenCalledWith('Unable to open the consent PDF.', 'error'));
    expect(tab.close).toHaveBeenCalled();
    expect(URL.createObjectURL).not.toHaveBeenCalled();
  });

  it('never passes wrapper objects directly to createObjectURL', async () => {
    const tab = { location: { href: '' }, close: vi.fn() };
    vi.spyOn(window, 'open').mockReturnValue(tab);
    render(<ParticipantConsentSection detail={recordedDetail} showToast={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'View PDF' }));
    await waitFor(() => expect(URL.createObjectURL).toHaveBeenCalled());
    const passed = URL.createObjectURL.mock.calls[0][0];
    expect(passed).toBeInstanceOf(Blob);
    expect(passed).not.toEqual(expect.objectContaining({ filename: expect.anything() }));
  });

  it('disables buttons during requests and prevents duplicate download clicks', async () => {
    let resolve;
    downloadConsent.mockReturnValue(new Promise(r => { resolve = r; }));
    render(<ParticipantConsentSection detail={recordedDetail} showToast={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Download PDF' }));
    expect(screen.getByRole('button', { name: 'Downloading…' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Downloading…' }));
    expect(downloadConsent).toHaveBeenCalledTimes(1);
    resolve(pdfPayload);
    await waitFor(() => expect(screen.getByRole('button', { name: 'Download PDF' })).not.toBeDisabled());
  });
});

describe('ParticipantsSection ZIP download', () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  beforeEach(() => {
    fetchDashboardParticipants.mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
    downloadAllConsents.mockResolvedValue(zipPayload);
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:zip');
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
  });

  it('passes a real Blob to createObjectURL for ZIP download', async () => {
    render(<ParticipantsSection showToast={vi.fn()} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Download All Consent Forms' }));
    await waitFor(() => expect(downloadAllConsents).toHaveBeenCalledTimes(1));
    expect(URL.createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
  });

  it('shows safe ZIP error and does not call createObjectURL on failure', async () => {
    downloadAllConsents.mockRejectedValue(new Error('bad'));
    const showToast = vi.fn();
    render(<ParticipantsSection showToast={showToast} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Download All Consent Forms' }));
    await waitFor(() => expect(showToast).toHaveBeenCalledWith('Unable to download the consent ZIP.', 'error'));
    expect(URL.createObjectURL).not.toHaveBeenCalled();
  });
});
