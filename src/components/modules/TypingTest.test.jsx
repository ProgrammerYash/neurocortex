import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ParticipantAppShell from '../participant/ParticipantAppShell.jsx';
import TypingTest from './TypingTest.jsx';

const LONG_PASSAGE =
  'The quick brown fox jumps over the lazy dog while the wind whispers through the tall grass '
  + 'and distant bells mark another hour in the quiet village beyond the river bend.';

vi.mock('../../constants/typingPassages.js', () => ({
  pickPassage: vi.fn(() => LONG_PASSAGE),
  roundTimeLimitSeconds: vi.fn(() => 120),
  adaptDifficulty: vi.fn((d) => d),
}));

function renderTyping(theme = 'dark') {
  const participantId = theme === 'light' ? 'P-LIGHT-TYPING' : 'P-DARK-TYPING';
  localStorage.setItem(
    'nc3_participant_themes',
    JSON.stringify({ [participantId]: theme }),
  );
  return render(
    <ParticipantAppShell participantId={participantId}>
      <TypingTest onComplete={vi.fn()} onBack={vi.fn()} locked={false} />
    </ParticipantAppShell>,
  );
}

async function startTypingRound() {
  fireEvent.click(await screen.findByRole('button', { name: /Begin Typing Test/i }));
  const passage = await waitFor(() => screen.getByTestId('typing-passage'));
  const input = screen.getByLabelText('Typing input');
  return { passage, input };
}

describe('TypingTest behavior', () => {
  let scrollIntoViewMock;

  beforeEach(() => {
    scrollIntoViewMock = vi.fn();
    Element.prototype.scrollIntoView = scrollIntoViewMock;
    window.matchMedia = vi.fn().mockImplementation((query) => ({
      matches: false,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it('passage uses wrap and vertical scroll without horizontal overflow', async () => {
    renderTyping('dark');
    const { passage } = await startTypingRound();
    expect(passage.style.overflowX).toBe('hidden');
    expect(passage.style.overflowY).toBe('auto');
    expect(passage.style.whiteSpace).toBe('pre-wrap');
    expect(passage.textContent?.length).toBeGreaterThan(80);
  });

  it('scrolls active character into view when position advances', async () => {
    renderTyping('dark');
    const { input } = await startTypingRound();
    scrollIntoViewMock.mockClear();
    fireEvent.keyDown(input, { key: LONG_PASSAGE[0] });
    await waitFor(() => expect(scrollIntoViewMock).toHaveBeenCalled());
    expect(scrollIntoViewMock.mock.calls.at(-1)[0]).toMatchObject({
      behavior: 'smooth',
      block: 'nearest',
      inline: 'nearest',
    });
  });

  it('uses immediate scrolling when reduced motion is preferred', async () => {
    window.matchMedia = vi.fn().mockImplementation((query) => ({
      matches: String(query).includes('prefers-reduced-motion'),
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
    renderTyping('dark');
    const { input } = await startTypingRound();
    scrollIntoViewMock.mockClear();
    fireEvent.keyDown(input, { key: LONG_PASSAGE[0] });
    await waitFor(() => expect(scrollIntoViewMock).toHaveBeenCalled());
    expect(scrollIntoViewMock.mock.calls.at(-1)[0].behavior).toBe('auto');
  });

  it('keeps focus on typing input and supports backspace', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    renderTyping('dark');
    const { input } = await startTypingRound();
    vi.advanceTimersByTime(100);
    await waitFor(() => expect(document.activeElement).toBe(input));
    fireEvent.keyDown(input, { key: LONG_PASSAGE[0] });
    fireEvent.keyDown(input, { key: LONG_PASSAGE[1] });
    fireEvent.keyDown(input, { key: 'Backspace' });
    expect(screen.getByText(/Backspaces: 1/)).toBeInTheDocument();
    vi.useRealTimers();
  });

  it('mobile-width container hides horizontal overflow on passage', async () => {
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 390, writable: true });
    renderTyping('dark');
    const { passage } = await startTypingRound();
    expect(passage.style.overflowX).toBe('hidden');
  });

  it('uses light participant tokens on passage and input in light theme', async () => {
    renderTyping('light');
    const { passage, input } = await startTypingRound();
    const shell = passage.closest('.participant-app');
    expect(shell?.className).toContain('participant-app--light');
    expect(passage.style.color).toBe('rgb(15, 23, 42)');
    expect(input.style.color).toBe('rgb(15, 23, 42)');
    expect(passage.style.background).not.toBe('rgb(19, 25, 40)');
  });

  it('uses dark theme tokens in dark mode', async () => {
    renderTyping('dark');
    const { passage } = await startTypingRound();
    const shell = passage.closest('.participant-app');
    expect(shell?.className).toContain('participant-app--dark');
    expect(passage.style.color).toBe('rgb(226, 232, 240)');
    expect(['rgb(19, 25, 40)', 'rgb(14, 20, 32)']).toContain(passage.style.background);
  });
});
