import { afterEach, describe, expect, it } from 'vitest';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { cleanup, render, screen } from '@testing-library/react';
import { RequireParticipant } from './RouteGuards.jsx';
import { ROUTES } from './routePaths.js';

function PathEcho() {
  const { pathname } = useLocation();
  return <div data-testid="pathname">{pathname}</div>;
}

function renderGuard(user, path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="*"
          element={(
            <>
              <PathEcho />
              <RequireParticipant user={user}>
                <div>Protected content</div>
              </RequireParticipant>
            </>
          )}
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe('RequireParticipant schedule guard', () => {
  afterEach(() => cleanup());

  const baseUser = {
    id: 'NC-TEST',
    role: 'participant',
    mustChangePin: false,
    consentRequired: false,
    consentRecorded: true,
  };

  it('redirects missing schedule to /participant/schedule', () => {
    renderGuard({ ...baseUser, studyFrequency: null }, ROUTES.participantDashboard);
    expect(screen.getByTestId('pathname').textContent).toBe(ROUTES.participantSchedule);
  });

  it('allows dashboard when schedule exists', () => {
    renderGuard({ ...baseUser, studyFrequency: 'daily' }, ROUTES.participantDashboard);
    expect(screen.getByTestId('pathname').textContent).toBe(ROUTES.participantDashboard);
    expect(screen.getByText('Protected content')).toBeInTheDocument();
  });
});
