import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ParticipantAiDataNotice from './ParticipantAiDataNotice.jsx';

describe('ParticipantAiDataNotice', () => {
  it('explains that sessions train the study AI model', () => {
    render(<ParticipantAiDataNotice />);
    expect(screen.getByRole('heading', { name: /your data and the ai model/i })).toBeInTheDocument();
    expect(screen.getByText(/train and improve the NeuroCortex AI model/i)).toBeInTheDocument();
  });
});
