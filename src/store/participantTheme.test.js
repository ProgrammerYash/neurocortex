import { describe, expect, it, beforeEach } from 'vitest';
import {
  getParticipantTheme,
  normalizeParticipantTheme,
  resolveParticipantTheme,
  setParticipantTheme,
} from './participantTheme.js';

describe('participantTheme storage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('always resolves to dark regardless of storage', () => {
    localStorage.setItem('nc3_participant_themes', JSON.stringify({ 'NC-ONE': 'light' }));
    expect(getParticipantTheme('NC-ONE')).toBe('dark');
    expect(normalizeParticipantTheme('light')).toBe('dark');
    expect(resolveParticipantTheme('system')).toBe('dark');
  });

  it('ignores setParticipantTheme writes', () => {
    setParticipantTheme('NC-ONE', 'light');
    expect(getParticipantTheme('NC-ONE')).toBe('dark');
  });
});
