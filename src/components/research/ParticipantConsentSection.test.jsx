import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ParticipantConsentSection from './ParticipantConsentSection.jsx';
import { downloadConsent, fetchConsentPdf } from '../../store/consent.js';

vi.mock('../../store/consent.js', () => ({
  fetchConsentPdf: vi.fn(),
  downloadConsent: vi.fn(),
}));

const recordedDetail = {
  participantId: 'NC-TEST-1',
  consentRecorded: true,
  consentRecordId: 'consent-1',
  consentVersion: 'v1',
  consentStudentSignedDisplay: 'Jul 20, 2026 10:00 PM',
  consentGuardianSignedDisplay: 'Jul 20, 2026 10:01 PM',
};

describe('ParticipantConsentSection', () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  beforeEach(() => {
    fetchConsentPdf.mockResolvedValue(new Blob(['%PDF'], { type: 'application/pdf' }));
    downloadConsent.mockResolvedValue(new Blob(['%PDF'], { type: 'application/pdf' }));
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:consent');
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    vi.spyOn(window, 'open').mockImplementation(() => null);
  });

  it('shows recorded consent controls', () => {
    render(<ParticipantConsentSection detail={recordedDetail} showToast={vi.fn()} />);
    expect(screen.getByText('Recorded')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'View PDF' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Download PDF' })).toBeInTheDocument();
  });

  it('hides controls when consent is missing', () => {
    render(<ParticipantConsentSection detail={{ participantId: 'NC-TEST-1', consentRecorded: false }} showToast={vi.fn()} />);
    expect(screen.getByText('No signed consent form.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'View PDF' })).not.toBeInTheDocument();
  });

  it('revokes object URLs after viewing PDF', async () => {
    render(<ParticipantConsentSection detail={recordedDetail} showToast={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'View PDF' }));
    await waitFor(() => expect(fetchConsentPdf).toHaveBeenCalledWith('consent-1'));
    expect(URL.createObjectURL).toHaveBeenCalled();
  });
});
