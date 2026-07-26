import { render, screen, cleanup } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import ResearchFeedbackCard from './ResearchFeedbackCard.jsx';
import { fetchParticipantModelFeedback } from '../../store/participantFeedback.js';

vi.mock('../../store/participantFeedback.js', () => ({
  fetchParticipantModelFeedback: vi.fn(),
}));

const NON_DIAGNOSTIC = 'research estimate';

describe('ResearchFeedbackCard API statuses', () => {
  afterEach(() => cleanup());

  it('shows not_released copy without diagnostic language', async () => {
    fetchParticipantModelFeedback.mockResolvedValue({ status: 'not_released' });
    render(<ResearchFeedbackCard />);
    const card = await screen.findByTestId('research-feedback-card');
    expect(card).toHaveTextContent(/has not been released/i);
    expect(card.textContent?.toLowerCase()).not.toMatch(/diagnos/);
  });

  it('renders insufficient_data with summary and warning', async () => {
    fetchParticipantModelFeedback.mockResolvedValue({
      status: 'insufficient_data',
      headline: 'More sessions needed',
      summary: 'Complete at least one full study session.',
      warning: `This is a ${NON_DIAGNOSTIC}, not medical advice.`,
    });
    render(<ResearchFeedbackCard />);
    expect(await screen.findByText('More sessions needed')).toBeInTheDocument();
    expect(screen.getByText(/Complete at least one full study session/i)).toBeInTheDocument();
    expect(screen.getAllByText(new RegExp(NON_DIAGNOSTIC, 'i')).length).toBeGreaterThan(0);
  });

  it('renders available feedback with level, factors, and warning', async () => {
    fetchParticipantModelFeedback.mockResolvedValue({
      status: 'available',
      level: 'moderate_load',
      headline: 'Patterns in your recent sessions',
      summary: 'Your recent reaction times varied slightly day to day.',
      factors: ['Reaction time trend', 'Sleep survey responses'],
      generated_at: '2026-07-20T12:00:00.000Z',
      warning: `This is a ${NON_DIAGNOSTIC}, not medical advice.`,
    });
    render(<ResearchFeedbackCard />);
    expect(await screen.findByText('Patterns in your recent sessions')).toBeInTheDocument();
    expect(screen.getByText('moderate load')).toBeInTheDocument();
    expect(screen.getByText('Reaction time trend')).toBeInTheDocument();
    expect(screen.getAllByText(new RegExp(NON_DIAGNOSTIC, 'i')).length).toBeGreaterThan(0);
    expect(screen.getByText(/Updated/i)).toBeInTheDocument();
  });
});
