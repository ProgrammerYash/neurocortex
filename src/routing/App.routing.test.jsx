import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import App from '../App.jsx';
import { ROUTES } from '../routing/routePaths.js';

function LocationEcho() {
  const { pathname } = useLocation();
  return <div data-testid="pathname">{pathname}</div>;
}

vi.mock('../store/index.js', async importOriginal => {
  const actual = await importOriginal();
  return {
    ...actual,
    default: {
      ...actual.default,
      clearAuth: vi.fn(),
      getSessions: vi.fn(async () => []),
      ensureGame: vi.fn(async () => null),
      loginParticipant: vi.fn(),
      loginResearcher: vi.fn(),
      registerParticipant: vi.fn(),
      getLocalParticipants: vi.fn(() => []),
      getParticipant: vi.fn(() => null),
    },
  };
});

vi.mock('../store/research.js', () => ({
  getTokenRole: vi.fn(() => null),
  isResearcherAuthed: vi.fn(() => false),
  fetchResearchParticipants: vi.fn(async () => []),
  fetchResearchSessions: vi.fn(async () => []),
}));

describe('App routing', () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it('renders PublicHome at / without hash', () => {
    render(
      <MemoryRouter initialEntries={[ROUTES.home]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByRole('heading', { level: 1, name: /NeuroCortex:/ })).toBeInTheDocument();
  });

  it('redirects unknown routes to home content', () => {
    render(
      <MemoryRouter initialEntries={['/does-not-exist']}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByRole('heading', { level: 1, name: /NeuroCortex:/ })).toBeInTheDocument();
  });

  it('shows participant sign-in at /participant/sign-in', () => {
    render(
      <MemoryRouter initialEntries={[ROUTES.participantSignIn]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByText('Enter your Participant ID')).toBeInTheDocument();
  });

  it('shows researcher sign-in at /researcher/sign-in', () => {
    render(
      <MemoryRouter initialEntries={[ROUTES.researcherSignIn]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByText('Researcher sign-in')).toBeInTheDocument();
  });

  it('navigates Join the Study to /join', () => {
    render(
      <MemoryRouter initialEntries={[ROUTES.home]}>
        <Routes>
          <Route path="*" element={<><App /><LocationEcho /></>} />
        </Routes>
      </MemoryRouter>,
    );
    fireEvent.click(screen.getAllByRole('button', { name: 'Join the Study' })[0]);
    expect(screen.getByTestId('pathname').textContent).toBe(ROUTES.join);
  });

  it('navigates Participant Sign In to /participant/sign-in', () => {
    render(
      <MemoryRouter initialEntries={[ROUTES.home]}>
        <Routes>
          <Route path="*" element={<><App /><LocationEcho /></>} />
        </Routes>
      </MemoryRouter>,
    );
    fireEvent.click(screen.getAllByRole('button', { name: 'Participant Sign In' })[0]);
    expect(screen.getByTestId('pathname').textContent).toBe(ROUTES.participantSignIn);
  });

  it('navigates Researcher access footer to /researcher/sign-in', () => {
    render(
      <MemoryRouter initialEntries={[ROUTES.home]}>
        <Routes>
          <Route path="*" element={<><App /><LocationEcho /></>} />
        </Routes>
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Researcher access' }));
    expect(screen.getByTestId('pathname').textContent).toBe(ROUTES.researcherSignIn);
  });
});
