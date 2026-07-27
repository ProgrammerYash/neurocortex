import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ParticipantSettings from './ParticipantSettings.jsx';
import { updateParticipantStudyFrequency } from '../../store/preferences.js';

const setTheme = vi.fn();

vi.mock('./ParticipantAppShell.jsx', async importOriginal => {
  const actual = await importOriginal();
  return {
    ...actual,
    useParticipantTheme: () => ({ theme: 'system', resolvedTheme: 'dark', setTheme }),
  };
});

vi.mock('../../store/preferences.js', () => ({
  updateParticipantStudyFrequency: vi.fn(),
}));

describe('ParticipantSettings', () => {
  afterEach(() => cleanup());

  it('uses System/Light/Dark order and single Save button', () => {
    render(
      <MemoryRouter>
        <ParticipantSettings user={{ studyFrequency: 'daily' }} showToast={vi.fn()} />
      </MemoryRouter>,
    );
    const labels = screen.getAllByRole('button', { name: 'System' });
    expect(labels.length).toBeGreaterThan(0);
    expect(screen.getByTestId('participant-settings-save')).toHaveTextContent('Save');
    expect(screen.queryByRole('button', { name: /Save Schedule/i })).not.toBeInTheDocument();
  });

  it('disables Save until draft changes and shows loading on save', async () => {
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
    fireEvent.click(screen.getByRole('button', { name: 'Light' }));
    expect(save).not.toBeDisabled();
    fireEvent.click(save);
    await waitFor(() => expect(setTheme).toHaveBeenCalledWith('light'));
  });
});
