import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ResearcherSignInScreen from './ResearcherSignInScreen.jsx';
import Store from '../../store/index.js';
import * as goldenVault from '../../store/goldenVault.js';

const navigate = vi.fn();

vi.mock('react-router-dom', async importOriginal => {
  const actual = await importOriginal();
  return {
    ...actual,
    useNavigate: () => navigate,
  };
});

vi.mock('../../store/index.js', () => ({
  default: {
    loginResearcher: vi.fn(),
  },
}));

vi.mock('../../store/goldenVault.js', async importOriginal => {
  const actual = await importOriginal();
  return {
    ...actual,
    loginGoldenVaultWithApi: vi.fn(),
  };
});

function fillAccessCode(container, value) {
  const input = container.querySelector('input[type="password"]');
  if (!input) throw new Error('password input not found');
  fireEvent.change(input, { target: { value } });
}

function submitForm(container) {
  const form = container.querySelector('form');
  if (!form) throw new Error('form not found');
  fireEvent.submit(form);
}

describe('ResearcherSignInScreen golden vault fallback', () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    navigate.mockReset();
    vi.mocked(Store.loginResearcher).mockReset();
    vi.mocked(goldenVault.loginGoldenVaultWithApi).mockReset();
  });

  it('redirects to golden vault when researcher login fails but vault code succeeds', async () => {
    const onLogin = vi.fn();
    vi.mocked(Store.loginResearcher).mockRejectedValue(new Error('Invalid researcher invite code'));
    vi.mocked(goldenVault.loginGoldenVaultWithApi).mockResolvedValue({ access_token: 'gv-token' });

    const { container } = render(
      <MemoryRouter>
        <ResearcherSignInScreen onLogin={onLogin} />
      </MemoryRouter>,
    );

    fillAccessCode(container, 'demo-vault-code');
    submitForm(container);

    await waitFor(() => {
      expect(goldenVault.loginGoldenVaultWithApi).toHaveBeenCalledWith({ code: 'demo-vault-code' });
      expect(navigate).toHaveBeenCalledWith('/golden-vault', { replace: true });
    });
  });

  it('shows alert when both researcher and golden vault login fail', async () => {
    const onLogin = vi.fn();
    vi.mocked(Store.loginResearcher).mockRejectedValue(new Error('Invalid researcher invite code'));
    vi.mocked(goldenVault.loginGoldenVaultWithApi).mockRejectedValue(new Error('Unauthorized'));

    const { container } = render(
      <MemoryRouter>
        <ResearcherSignInScreen onLogin={onLogin} />
      </MemoryRouter>,
    );

    fillAccessCode(container, 'bad-code');
    submitForm(container);

    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(navigate).not.toHaveBeenCalledWith('/golden-vault', expect.anything());
  });
});
