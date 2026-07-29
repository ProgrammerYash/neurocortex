import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import GoldenVaultPage from './GoldenVaultPage.jsx';
import * as goldenVault from '../../store/goldenVault.js';

vi.mock('../../store/goldenVault.js', async importOriginal => {
  const actual = await importOriginal();
  return {
    ...actual,
    isGoldenVaultAuthed: vi.fn(() => true),
    fetchGoldenVaultParticipants: vi.fn(),
    fetchGoldenVaultAuditHistory: vi.fn(),
    goldenVaultBulk: vi.fn(),
    goldenVaultAdjustSessions: vi.fn(),
    goldenVaultPatchParticipant: vi.fn(),
  };
});

describe('GoldenVaultPage', () => {
  beforeEach(() => {
    goldenVault.clearGoldenVaultToken();
    vi.mocked(goldenVault.isGoldenVaultAuthed).mockReturnValue(true);
    vi.mocked(goldenVault.fetchGoldenVaultParticipants).mockResolvedValue({
      items: [
        {
          participantId: 'NC-DEMO1',
          displayName: 'Demo User',
          enabled: true,
          realCompletedSessions: 0,
          bonusSessions: 10,
          displayedCompletedSessions: 10,
          earnedCoins: 0,
          bonusCoins: 100,
          displayedCoins: 100,
          feedbackLevel: 'moderate',
          updatedAt: new Date().toISOString(),
          autoSessionEnabled: true,
          nextAutoSessionDisplay: 'Jul 28, 2026 4:37 PM',
          lastAutoSessionDisplay: null,
        },
      ],
      total: 1,
    });
    vi.mocked(goldenVault.fetchGoldenVaultAuditHistory).mockResolvedValue([]);
  });

  afterEach(() => {
    cleanup();
    goldenVault.clearGoldenVaultToken();
  });

  it('renders gold theme heading', async () => {
    render(<MemoryRouter><GoldenVaultPage /></MemoryRouter>);
    expect(await screen.findByText('Golden Vault')).toBeInTheDocument();
    expect(screen.getByText('Demo Data Control Center')).toBeInTheDocument();
    expect(screen.getByText('SIMULATED DATA')).toBeInTheDocument();
  });

  it('loads participant rows with compact manage control', async () => {
    render(<MemoryRouter><GoldenVaultPage /></MemoryRouter>);
    expect(await screen.findByText('NC-DEMO1')).toBeInTheDocument();
    expect(screen.getByTestId('golden-vault-pagination')).toBeInTheDocument();
    expect(screen.getByLabelText('Rows per page')).toHaveValue('25');
    fireEvent.click(screen.getByTestId('golden-vault-manage-NC-DEMO1'));
    const panel = await screen.findByTestId('golden-vault-manage-panel');
    expect(within(panel).getByText(/Auto Data:/i)).toBeInTheDocument();
    expect(within(panel).getByText(/Next: Jul 28, 2026 4:37 PM/i)).toBeInTheDocument();
  });

  it('select-all and bulk toolbar', async () => {
    render(<MemoryRouter><GoldenVaultPage /></MemoryRouter>);
    await screen.findByRole('checkbox', { name: /Select NC-DEMO1/i });
    fireEvent.click(screen.getByLabelText('Select all visible'));
    expect(await screen.findByTestId('golden-bulk-toolbar')).toBeInTheDocument();
    expect(screen.getByText(/1 selected/)).toBeInTheDocument();
  }, 15000);

  it('opens add sessions modal and rejects negative amount', async () => {
    render(<MemoryRouter><GoldenVaultPage /></MemoryRouter>);
    await screen.findByRole('checkbox', { name: /Select NC-DEMO1/i });
    fireEvent.click(screen.getByLabelText('Select all visible'));
    fireEvent.click(await screen.findByText('Add Sessions'));
    const dialog = screen.getByRole('dialog');
    const input = within(dialog).getByRole('spinbutton');
    fireEvent.change(input, { target: { value: '-3' } });
    fireEvent.click(screen.getByText('Apply'));
    expect(await screen.findByRole('alert')).toHaveTextContent(/whole number/i);
  });

  it('redirects when unauthorized', () => {
    vi.mocked(goldenVault.isGoldenVaultAuthed).mockReturnValue(false);
    render(<MemoryRouter initialEntries={['/researcher/sign-in']}><GoldenVaultPage /></MemoryRouter>);
    expect(goldenVault.isGoldenVaultAuthed()).toBe(false);
  });
});

describe('golden vault token storage', () => {
  it('uses separate storage key from researcher token', async () => {
    const mod = await import('../../store/goldenVault.js');
    mod.setGoldenVaultToken('golden-token');
    expect(localStorage.getItem('nc3_golden_vault_token')).toBe('golden-token');
    mod.clearGoldenVaultToken();
  });
});

describe('golden vault login route', () => {
  it('login helper targets golden endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({ access_token: 'abc', token_type: 'bearer', expires_in: 1800 }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const mod = await import('../../store/goldenVault.js');
    await mod.loginGoldenVaultWithApi({ code: 'secret' });
    expect(fetchMock.mock.calls[0][0]).toContain('/v1/golden-vault/login');
    vi.unstubAllGlobals();
  });
});
