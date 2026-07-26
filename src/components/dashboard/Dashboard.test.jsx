import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Dashboard from './Dashboard.jsx';
import { fetchMyConsentStatus } from '../../store/consent.js';
import { fetchUnreadMessageCount } from '../../store/messages.js';
import { fetchParticipantModelFeedback } from '../../store/participantFeedback.js';

vi.mock('../../store/consent.js', () => ({
  fetchMyConsentStatus: vi.fn(),
}));

vi.mock('../../store/messages.js', () => ({
  fetchUnreadMessageCount: vi.fn(),
}));

vi.mock('../../store/participantFeedback.js', () => ({
  fetchParticipantModelFeedback: vi.fn(),
}));

const baseGameData = {
  coins: 42,
  streak: 3,
  totalDays: 5,
  pet: {
    type: 'fox',
    name: 'Spark',
    level: 2,
    evolution: 'baby',
    happiness: 80,
    energy: 70,
    xp: 25,
  },
};

const baseProps = {
  user: { id: 'NC-TEST-1', studyFrequency: 'daily' },
  sessions: [],
  todaySessions: {},
  todayComplete: false,
  gameData: baseGameData,
  countdown: null,
  onNavigate: vi.fn(),
  onLogout: vi.fn(),
  showToast: vi.fn(),
};

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchMyConsentStatus.mockResolvedValue({
      consent_recorded: true,
      session_eligible: true,
    });
    fetchUnreadMessageCount.mockResolvedValue({ unread_count: 0 });
    fetchParticipantModelFeedback.mockResolvedValue({ status: 'disabled' });
  });

  it('renders without crashing when game data includes the pet banner', async () => {
    render(
      <MemoryRouter>
        <Dashboard {...baseProps} />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Spark')).toBeInTheDocument();
    expect(screen.getByText(/Your data and the AI model/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Sign Out/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Today' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Enrollment' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Progress' })).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /NeuroVerse/i })).toHaveLength(1);
  });
});
