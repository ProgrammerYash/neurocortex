import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ParticipantMessaging from './ParticipantMessaging.jsx';
import { fetchSentParticipantMessages, sendParticipantMessage } from '../../store/messages.js';

vi.mock('../../store/messages.js', () => ({
  fetchSentParticipantMessages: vi.fn(),
  sendParticipantMessage: vi.fn(),
}));

const detail = {
  participantId: 'NC-TEST-1',
  studentName: 'Test Student',
  isRemoved: false,
};

describe('ParticipantMessaging', () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  beforeEach(() => {
    fetchSentParticipantMessages.mockResolvedValue({
      items: [{
        id: 'msg-1',
        subject: 'Hello',
        body: 'Body text',
        createdAtDisplay: 'Jul 20, 2026 10:00 PM',
        isRead: false,
      }],
    });
  });

  it('shows Send Message button', async () => {
    render(<ParticipantMessaging detail={detail} showToast={vi.fn()} />);
    expect(await screen.findByRole('button', { name: 'Send Message' })).toBeInTheDocument();
  });

  it('validates subject and body before sending', async () => {
    render(<ParticipantMessaging detail={detail} showToast={vi.fn()} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Send Message' }));
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled();
  });

  it('disables send while processing to prevent double send', async () => {
    let resolve;
    sendParticipantMessage.mockReturnValue(new Promise(r => { resolve = r; }));
    render(<ParticipantMessaging detail={detail} showToast={vi.fn()} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Send Message' }));
    fireEvent.change(screen.getByLabelText(/subject/i), { target: { value: 'Subject' } });
    fireEvent.change(screen.getByLabelText(/message/i), { target: { value: 'Body text' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));
    expect(screen.getByRole('button', { name: 'Sending…' })).toBeDisabled();
    resolve({});
    await waitFor(() => expect(sendParticipantMessage).toHaveBeenCalledTimes(1));
  });

  it('clears composer after success', async () => {
    sendParticipantMessage.mockResolvedValue({});
    const showToast = vi.fn();
    render(<ParticipantMessaging detail={detail} showToast={showToast} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Send Message' }));
    fireEvent.change(screen.getByLabelText(/subject/i), { target: { value: 'Subject' } });
    fireEvent.change(screen.getByLabelText(/message/i), { target: { value: 'Body text' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));
    await waitFor(() => expect(showToast).toHaveBeenCalled());
    expect(screen.queryByLabelText(/subject/i)).not.toBeInTheDocument();
  });

  it('renders sent message history and read status', async () => {
    render(<ParticipantMessaging detail={detail} showToast={vi.fn()} />);
    expect(await screen.findByText('Hello')).toBeInTheDocument();
    expect(screen.getByText('Unread')).toBeInTheDocument();
  });
});
