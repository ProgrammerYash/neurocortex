import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ResearcherDashboard from './ResearcherDashboard.jsx';
import ParticipantsSection from './ParticipantsSection.jsx';
import {
  fetchDashboardParticipantDetail,
  fetchDashboardParticipants,
  fetchDashboardSummary,
  fetchGroqProviderStatus,
  fetchParticipantAccountActions,
} from '../../store/research.js';

vi.mock('../../store/research.js', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    fetchDashboardSummary: vi.fn(),
    fetchDashboardParticipants: vi.fn(),
    fetchDashboardParticipantDetail: vi.fn(),
    fetchParticipantAccountActions: vi.fn(),
    fetchGroqProviderStatus: vi.fn(),
    bulkMessageParticipants: vi.fn(),
    bulkEmailParticipants: vi.fn(),
    bulkReleaseFeedback: vi.fn(),
    bulkRevokeFeedback: vi.fn(),
    bulkRefreshFeedback: vi.fn(),
    bulkSuspendParticipants: vi.fn(),
    bulkReactivateParticipants: vi.fn(),
    bulkRemoveParticipants: vi.fn(),
    releaseParticipantFeedback: vi.fn(),
    refreshParticipantFeedback: vi.fn(),
    revokeParticipantFeedback: vi.fn(),
  };
});

vi.mock('../../store/consent.js', () => {
  const pdfPayload = {
    blob: new Blob(['%PDF'], { type: 'application/pdf' }),
    filename: 'NC-TEST-1-consent.pdf',
    contentType: 'application/pdf',
  };
  return {
    fetchConsentPdf: vi.fn(async () => pdfPayload),
    downloadConsent: vi.fn(async () => pdfPayload),
    downloadAllConsents: vi.fn(),
  };
});

const summary = {
  totalParticipants: 2,
  totalSessions: 3,
  totalCompletedSessions: 2,
  activeParticipants7d: 1,
  averageSessionCompletion: 66.7,
  averageReactionTimeMs: 245,
  averageStress: 6.4,
  averageFatigue: 5.2,
  averageSleepHours: 7.3,
  averageMemoryAccuracy: 84.7,
  groqFeedbackStatus: 'not_configured',
  groqFeedbackConfigured: false,
  groqModel: null,
};

const participantRow = {
  participantId: 'NC-TEST-1',
  studentName: 'Student One',
  guardianName: 'Guardian One',
  grade: '10th Grade',
  ageRange: '15',
  ageDisplay: '15',
  joinedDisplay: 'Jul 19, 2026',
  sessions: 2,
  lastActiveDisplay: 'Jul 19, 2026 3:00 PM',
  status: 'Active',
  averageReactionTimeMs: 245,
  averageStress: 6.4,
  averageFatigue: 5.2,
  averageSleepHours: 7.3,
  averageMemoryAccuracy: 84.7,
  sessionCompletion: 50,
  feedbackStatus: 'Released',
};

describe('ResearcherDashboard', () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  beforeEach(() => {
    fetchDashboardSummary.mockResolvedValue(summary);
    fetchGroqProviderStatus.mockResolvedValue({
      configured: false,
      provider: 'Groq',
      status: 'not_configured',
      model: null,
    });
    fetchDashboardParticipants.mockResolvedValue({ items: [participantRow], total: 1, limit: 20, offset: 0 });
    fetchParticipantAccountActions.mockResolvedValue({ items: [] });
    fetchDashboardParticipantDetail.mockResolvedValue({
      ...participantRow,
      sessionsStarted: 2,
      sessionsCompleted: 1,
      recentSessions: [{
        date: '2026-07-19',
        reactionCompleted: true,
        typingCompleted: true,
        memoryCompleted: false,
        attentionCompleted: false,
        surveyCompleted: false,
        complete: false,
      }],
    });
  });

  it('renders summary cards without tab navigation', async () => {
    render(<ResearcherDashboard onBack={() => {}} />);
    expect(await screen.findByText('Total Participants')).toBeInTheDocument();
    expect(await screen.findByText('Groq Participant Feedback')).toBeInTheDocument();
    expect(await screen.findByText('Completed Sessions')).toBeInTheDocument();
    expect(screen.getByText('Average Memory Accuracy')).toBeInTheDocument();
    expect(screen.queryByText('ML / SHAP')).not.toBeInTheDocument();
    expect(screen.queryByText('Consent Forms')).not.toBeInTheDocument();
  });

  it('shows loading, empty, error, table, details, and pagination in participants section', async () => {
    render(<ParticipantsSection />);
    const table = await screen.findByRole('table');
    expect(within(table).getByText('Student One')).toBeInTheDocument();
    expect(within(table).getByText('245 ms')).toBeInTheDocument();
    expect(within(table).getByText('6.4 / 10')).toBeInTheDocument();
    expect(within(table).getByText('7.3 hrs')).toBeInTheDocument();
    expect(within(table).getByText('84.7%')).toBeInTheDocument();
    expect(screen.queryByText('Session Completion')).not.toBeInTheDocument();
    expect(screen.queryByText('Average Session Completion')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'View' }));
    expect(await screen.findByText('Recent session history')).toBeInTheDocument();
    expect(screen.getByText('Student name:')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Search participants'), { target: { value: 'Student One' } });
    await waitFor(() => expect(fetchDashboardParticipants).toHaveBeenCalled());
  });

  it('shows download all consent forms on participants section without separate tab', async () => {
    render(<ParticipantsSection />);
    expect(await screen.findByRole('button', { name: 'Download All Consent Forms' })).toBeInTheDocument();
    expect(screen.queryByText('Consent Forms')).not.toBeInTheDocument();
  });

  it('does not expose participant type filter or synthetic badges on researcher dashboard', async () => {
    fetchDashboardParticipants.mockResolvedValue({
      items: [{ ...participantRow, participantId: 'NC-SYN-1', participantType: 'synthetic_demo' }],
      total: 1,
      limit: 20,
      offset: 0,
    });
    render(<ResearcherDashboard onBack={() => {}} />);
    await screen.findByText('NC-SYN-1');
    expect(screen.queryByLabelText('Participant type filter')).not.toBeInTheDocument();
    expect(screen.queryByText('Synthetic Demo')).not.toBeInTheDocument();
    expect(fetchDashboardParticipants).toHaveBeenCalledWith(
      expect.not.objectContaining({ participantType: expect.anything() }),
    );
  });

  it('shows empty and retry states', async () => {
    fetchDashboardParticipants.mockResolvedValueOnce({ items: [], total: 0, limit: 20, offset: 0 });
    const { unmount } = render(<ParticipantsSection />);
    expect(await screen.findByText('No participants have enrolled yet.')).toBeInTheDocument();

    unmount();
    fetchDashboardParticipants.mockRejectedValueOnce(new Error('Network down'));
    render(<ParticipantsSection />);
    expect(await screen.findByText('Network down')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
  });
});
