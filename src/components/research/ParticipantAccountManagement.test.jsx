import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ParticipantAccountManagement from './ParticipantAccountManagement.jsx';
import {
  disableParticipantAccount,
  enableParticipantAccount,
  fetchParticipantAccountActions,
  removeParticipantAccount,
  resetParticipantPin,
  suspendParticipantAccount,
} from '../../store/research.js';

vi.mock('../../store/research.js', () => ({
  fetchParticipantAccountActions: vi.fn(),
  suspendParticipantAccount: vi.fn(),
  unsuspendParticipantAccount: vi.fn(),
  resetParticipantPin: vi.fn(),
  disableParticipantAccount: vi.fn(),
  enableParticipantAccount: vi.fn(),
  removeParticipantAccount: vi.fn(),
}));

const activeDetail = {
  participantId: 'NC-TEST-1',
  status: 'Active',
  isSuspended: false,
  isDisabled: false,
  isRemoved: false,
};

describe('ParticipantAccountManagement', () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  beforeEach(() => {
    fetchParticipantAccountActions.mockResolvedValue({ items: [] });
  });

  it('shows management actions for active accounts', async () => {
    render(<ParticipantAccountManagement detail={activeDetail} onUpdated={vi.fn()} />);
    expect(await screen.findByRole('button', { name: 'Suspend' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reset PIN' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Disable Account' })).toBeInTheDocument();
  });

  it('shows unsuspend for suspended accounts', async () => {
    render(<ParticipantAccountManagement detail={{ ...activeDetail, status: 'Suspended', isSuspended: true }} onUpdated={vi.fn()} />);
    expect(await screen.findByRole('button', { name: 'Unsuspend' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Suspend' })).not.toBeInTheDocument();
  });

  it('validates suspend reason and remove confirmation', async () => {
    const onUpdated = vi.fn();
    render(<ParticipantAccountManagement detail={activeDetail} onUpdated={onUpdated} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Suspend' }));
    const confirm = screen.getByRole('button', { name: 'Confirm suspend' });
    expect(confirm).toBeDisabled();
    fireEvent.change(screen.getAllByRole('textbox')[0], { target: { value: 'Valid reason here' } });
    expect(confirm).not.toBeDisabled();
    suspendParticipantAccount.mockResolvedValue({});
    fireEvent.click(confirm);
    await waitFor(() => expect(suspendParticipantAccount).toHaveBeenCalled());

    fireEvent.click(screen.getByRole('button', { name: 'Remove Account' }));
    const removeBtn = screen.getByRole('button', { name: 'Remove account access' });
    expect(removeBtn).toBeDisabled();
    const textboxes = screen.getAllByRole('textbox');
    fireEvent.change(textboxes[textboxes.length - 2], { target: { value: 'Requested removal reason' } });
    fireEvent.change(textboxes[textboxes.length - 1], { target: { value: 'NC-TEST-1' } });
    expect(removeBtn).not.toBeDisabled();
  });

  it('shows temporary PIN once and clears on close', async () => {
    resetParticipantPin.mockResolvedValue({ temporaryPin: '123456' });
    render(<ParticipantAccountManagement detail={activeDetail} onUpdated={vi.fn()} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Reset PIN' }));
    fireEvent.click(screen.getAllByRole('button', { name: 'Reset PIN' })[1]);
    expect(await screen.findByDisplayValue('123456')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Close' }));
    expect(screen.queryByDisplayValue('123456')).not.toBeInTheDocument();
  });
});
