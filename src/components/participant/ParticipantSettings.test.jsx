import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ParticipantSettings from './ParticipantSettings.jsx';
import { updateParticipantStudyFrequency } from '../../store/preferences.js';

vi.mock('../../store/preferences.js', () => ({
  updateParticipantStudyFrequency: vi.fn(),
}));

describe('ParticipantSettings', () => {
  afterEach(() => cleanup());

  it('does not render theme selector and uses single Save button', () => {
    render(
      <MemoryRouter>
        <ParticipantSettings user={{ studyFrequency: 'daily' }} showToast={vi.fn()} />
      </MemoryRouter>,
    );
    expect(screen.queryByText('Appearance')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Light' })).not.toBeInTheDocument();
    expect(screen.getByTestId('participant-settings-save')).toHaveTextContent('Save');
  });

  it('disables Save until schedule changes and saves frequency', async () => {
    updateParticipantStudyFrequency.mockResolvedValue({ study_frequency: 'weekly' });
    render(
      <MemoryRouter>
        <ParticipantSettings
          user={{ studyFrequency: 'daily' }}
          onStudyFrequencySaved={vi.fn()}
          showToast={vi.fn()}
        />
      </MemoryRouter>,
    );
    const save = screen.getByTestId('participant-settings-save');
    expect(save).toBeDisabled();
    fireEvent.click(screen.getByRole('radio', { name: /^Weekly/i }));
    expect(save).not.toBeDisabled();
    fireEvent.click(save);
    await waitFor(() => expect(updateParticipantStudyFrequency).toHaveBeenCalledWith('weekly'));
  });
});
