import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import StudyProgressTab from './StudyProgressTab.jsx';
import ParticipantAppShell from '../participant/ParticipantAppShell.jsx';
import { fetchMyStudyProgress } from '../../store/consent.js';

vi.mock('../../store/consent.js', () => ({
  fetchMyStudyProgress: vi.fn(),
}));

describe('StudyProgressTab weekly progress', () => {
  beforeEach(() => {
    fetchMyStudyProgress.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('shows completed sessions this week from backend fields', async () => {
    fetchMyStudyProgress.mockResolvedValue({
      completed_sessions: 12,
      required_sessions: 90,
      study_status: 'in_progress',
      today_session_complete: false,
      session_can_start: true,
      completed_this_week: 3,
      weekly_target: 5,
      week_start: '2026-07-21',
      week_end: '2026-07-27',
    });

    render(
      <ParticipantAppShell participantId="P-TEST">
        <StudyProgressTab />
      </ParticipantAppShell>,
    );

    expect(await screen.findByTestId('weekly-session-progress')).toHaveTextContent(
      'Completed sessions this week: 3 / 5',
    );
    expect(screen.getByText(/Week of/i)).toBeInTheDocument();
  });

  it('omits weekly row when weekly_target is null', async () => {
    fetchMyStudyProgress.mockResolvedValue({
      completed_sessions: 1,
      required_sessions: 90,
      study_status: 'in_progress',
      today_session_complete: false,
      session_can_start: true,
      completed_this_week: 0,
      weekly_target: null,
    });

    render(
      <ParticipantAppShell participantId="P-TEST">
        <StudyProgressTab />
      </ParticipantAppShell>,
    );

    await screen.findByText(/Status:/);
    expect(screen.queryByTestId('weekly-session-progress')).not.toBeInTheDocument();
    expect(screen.queryByText(/Completed sessions:/)).not.toBeInTheDocument();
  });

  it('never shows cumulative completed sessions X / Y', async () => {
    fetchMyStudyProgress.mockResolvedValue({
      completed_sessions: 1,
      required_sessions: 14,
      study_status: 'in_progress',
      today_session_complete: false,
      session_can_start: true,
      completed_this_week: 1,
      weekly_target: 2,
    });

    render(
      <ParticipantAppShell participantId="P-TEST">
        <StudyProgressTab />
      </ParticipantAppShell>,
    );

    await screen.findByTestId('weekly-session-progress');
    expect(screen.queryByText(/Completed sessions: 1 \/ 14/)).not.toBeInTheDocument();
  });
});
