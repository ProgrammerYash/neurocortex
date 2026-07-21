import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ParticipantInbox from './ParticipantInbox.jsx';
import {
  fetchParticipantMessages,
  fetchUnreadMessageCount,
  markMessageRead,
} from '../../store/messages.js';

vi.mock('../../store/messages.js', () => ({
  fetchParticipantMessages: vi.fn(),
  fetchUnreadMessageCount: vi.fn(),
  markMessageRead: vi.fn(),
}));

describe('ParticipantInbox', () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  beforeEach(() => {
    fetchUnreadMessageCount.mockResolvedValue({ unread_count: 2 });
    fetchParticipantMessages.mockResolvedValue({
      items: [{
        id: 'msg-1',
        subject: 'Reminder',
        body: 'Please complete today\'s modules.',
        createdAtDisplay: 'Jul 20, 2026 10:00 PM',
        isRead: false,
      }],
    });
    markMessageRead.mockResolvedValue({
      id: 'msg-1',
      subject: 'Reminder',
      body: 'Please complete today\'s modules.',
      createdAtDisplay: 'Jul 20, 2026 10:00 PM',
      isRead: true,
    });
  });

  it('shows inbox heading', async () => {
    render(<ParticipantInbox onBack={vi.fn()} onUnreadChange={vi.fn()} showToast={vi.fn()} />);
    expect(await screen.findByText('Messages')).toBeInTheDocument();
  });

  it('shows unread badge count from API', async () => {
    const onUnreadChange = vi.fn();
    render(<ParticipantInbox onBack={vi.fn()} onUnreadChange={onUnreadChange} showToast={vi.fn()} />);
    await waitFor(() => expect(onUnreadChange).toHaveBeenCalledWith(2));
  });

  it('marks message read when opened and updates unread count', async () => {
    const onUnreadChange = vi.fn();
    fetchUnreadMessageCount
      .mockResolvedValueOnce({ unread_count: 2 })
      .mockResolvedValueOnce({ unread_count: 1 });
    render(<ParticipantInbox onBack={vi.fn()} onUnreadChange={onUnreadChange} showToast={vi.fn()} />);
    fireEvent.click(await screen.findByText('Reminder'));
    await waitFor(() => expect(markMessageRead).toHaveBeenCalledWith('msg-1'));
    await waitFor(() => expect(onUnreadChange).toHaveBeenCalledWith(1));
  });

  it('shows empty inbox state', async () => {
    fetchParticipantMessages.mockResolvedValue({ items: [] });
    render(<ParticipantInbox onBack={vi.fn()} onUnreadChange={vi.fn()} showToast={vi.fn()} />);
    expect(await screen.findByText('No messages yet.')).toBeInTheDocument();
  });

  it('shows error and retry state', async () => {
    fetchParticipantMessages.mockRejectedValue(new Error('Network error'));
    render(<ParticipantInbox onBack={vi.fn()} onUnreadChange={vi.fn()} showToast={vi.fn()} />);
    expect(await screen.findByText('Network error')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();
  });

  it('does not expose reply or compose controls', async () => {
    render(<ParticipantInbox onBack={vi.fn()} onUnreadChange={vi.fn()} showToast={vi.fn()} />);
    await screen.findByText('Reminder');
    expect(screen.queryByRole('button', { name: /reply/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /compose/i })).not.toBeInTheDocument();
  });
});
