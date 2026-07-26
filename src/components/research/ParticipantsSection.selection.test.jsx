import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ParticipantsSection from './ParticipantsSection.jsx';
import { fetchDashboardParticipants, fetchGroqProviderStatus } from '../../store/research.js';

vi.mock('../../store/research.js', () => ({
  fetchDashboardParticipants: vi.fn(),
  fetchDashboardParticipantDetail: vi.fn(),
  fetchGroqProviderStatus: vi.fn(),
  buildBulkSelectionPayload: vi.fn(payload => payload),
  bulkMessageParticipants: vi.fn(),
  bulkEmailParticipants: vi.fn(),
  bulkReleaseFeedback: vi.fn(),
  bulkRevokeFeedback: vi.fn(),
  bulkRefreshFeedback: vi.fn(),
  bulkSuspendParticipants: vi.fn(),
  bulkReactivateParticipants: vi.fn(),
  bulkRemoveParticipants: vi.fn(),
}));

vi.mock('../../store/consent.js', () => ({
  downloadAllConsents: vi.fn(),
}));

const rowA = {
  participantId: 'NC-SEL-A',
  studentName: 'Alpha',
  guardianName: 'G1',
  grade: '9th Grade',
  ageRange: '14',
  ageDisplay: '14',
  joinedDisplay: 'Jul 1, 2026',
  sessions: 1,
  lastActiveDisplay: 'Jul 1, 2026',
  status: 'Active',
  feedbackStatus: 'Released',
  sessionCompletion: 100,
  consentRecorded: true,
};

const rowB = {
  ...rowA,
  participantId: 'NC-SEL-B',
  studentName: 'Beta',
  feedbackStatus: 'Not Released',
};

describe('ParticipantsSection bulk selection', () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  beforeEach(() => {
    fetchGroqProviderStatus.mockResolvedValue({ configured: true, status: 'ready', model: 'test' });
    fetchDashboardParticipants.mockResolvedValue({ items: [rowA, rowB], total: 50, limit: 20, offset: 0 });
    Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: 1200 });
  });

  it('renders row checkboxes and selects an individual participant', async () => {
    render(<ParticipantsSection showToast={vi.fn()} groqReady />);
    const rowCheckbox = await screen.findByRole('checkbox', { name: 'Select NC-SEL-A' });
    expect(rowCheckbox).toBeInTheDocument();
    fireEvent.click(rowCheckbox);
    expect(await screen.findByText('1 selected')).toBeInTheDocument();
    expect(screen.getByTestId('participant-bulk-toolbar')).toBeInTheDocument();
  });

  it('header select-all selects visible page and supports indeterminate state', async () => {
    render(<ParticipantsSection showToast={vi.fn()} groqReady />);
    const header = await screen.findByRole('checkbox', { name: 'Select all on page' });
    fireEvent.click(header);
    expect(await screen.findByText('2 selected')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('checkbox', { name: 'Select NC-SEL-A' }));
    expect(await screen.findByText('1 selected')).toBeInTheDocument();
    expect(header.indeterminate).toBe(true);
  });

  it('shows select-all-matching banner and clears selection', async () => {
    render(<ParticipantsSection showToast={vi.fn()} groqReady />);
    fireEvent.click(await screen.findByRole('checkbox', { name: 'Select all on page' }));
    expect(await screen.findByText(/Select all 50 matching participants/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Select all 50 matching participants/i }));
    expect(await screen.findByText('50 selected')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Clear selection' }));
    await waitFor(() => expect(screen.queryByTestId('participant-bulk-toolbar')).not.toBeInTheDocument());
  });

  it('clears selection when filters change', async () => {
    render(<ParticipantsSection showToast={vi.fn()} groqReady />);
    fireEvent.click(await screen.findByRole('checkbox', { name: 'Select NC-SEL-B' }));
    expect(await screen.findByText('1 selected')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Status filter'), { target: { value: 'suspended' } });
    await waitFor(() => expect(screen.queryByTestId('participant-bulk-toolbar')).not.toBeInTheDocument());
  });

  it('row checkbox click does not open participant details', async () => {
    const { fetchDashboardParticipantDetail } = await import('../../store/research.js');
    render(<ParticipantsSection showToast={vi.fn()} groqReady />);
    fireEvent.click(await screen.findByRole('checkbox', { name: 'Select NC-SEL-A' }));
    expect(fetchDashboardParticipantDetail).not.toHaveBeenCalled();
  });

  it('shows real feedback status labels in the table', async () => {
    render(<ParticipantsSection showToast={vi.fn()} groqReady />);
    expect(await screen.findByText('Released')).toBeInTheDocument();
    expect(screen.getByText('Not Released')).toBeInTheDocument();
  });
});
