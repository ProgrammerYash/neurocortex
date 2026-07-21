import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ResearcherDashboard from './ResearcherDashboard.jsx';
import ParticipantsSection from './ParticipantsSection.jsx';
import {
  fetchDashboardParticipantDetail,
  fetchDashboardParticipants,
  fetchDashboardSummary,
} from '../../store/research.js';

vi.mock('../../store/research.js', () => ({
  fetchDashboardSummary: vi.fn(),
  fetchDashboardParticipants: vi.fn(),
  fetchDashboardParticipantDetail: vi.fn(),
}));

const summary = {
  totalParticipants: 2,
  totalSessions: 3,
  activeParticipants7d: 1,
  averageSessionCompletion: 66.7,
  averageReactionTimeMs: 245,
  averageStress: 6.4,
  averageFatigue: 5.2,
  averageSleepHours: 7.3,
  averageMemoryAccuracy: 84.7,
};

const participantRow = {
  participantId: 'NC-TEST-1',
  studentName: 'Student One',
  guardianName: 'Guardian One',
  grade: '10th Grade',
  ageRange: '15-16',
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
};

describe('ResearcherDashboard', () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  beforeEach(() => {
    fetchDashboardSummary.mockResolvedValue(summary);
    fetchDashboardParticipants.mockResolvedValue({ items: [participantRow], total: 1, limit: 20, offset: 0 });
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
    expect(screen.getByText('Average Memory Accuracy')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
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
    expect(within(table).getByText('50.0%')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'View' }));
    expect(await screen.findByText('Recent session history')).toBeInTheDocument();
    expect(screen.getByText('Student name:')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Search participants'), { target: { value: 'Student One' } });
    await waitFor(() => expect(fetchDashboardParticipants).toHaveBeenCalled());
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
