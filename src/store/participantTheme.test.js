import { describe, expect, it, beforeEach } from 'vitest';
import { getParticipantTheme, setParticipantTheme } from './participantTheme.js';

describe('participantTheme storage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('defaults to dark', () => {
    expect(getParticipantTheme('NC-ONE')).toBe('dark');
  });

  it('persists light and dark per participant', () => {
    setParticipantTheme('NC-ONE', 'light');
    setParticipantTheme('NC-TWO', 'dark');
    expect(getParticipantTheme('NC-ONE')).toBe('light');
    expect(getParticipantTheme('NC-TWO')).toBe('dark');
  });

  it('handles malformed storage safely', () => {
    localStorage.setItem('nc3_participant_themes', '{bad');
    expect(getParticipantTheme('NC-ONE')).toBe('dark');
  });
});
