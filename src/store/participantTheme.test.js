import { describe, expect, it, beforeEach, vi } from 'vitest';
import {
  applySystemTheme,
  getParticipantTheme,
  normalizeParticipantTheme,
  resolveParticipantTheme,
  setParticipantTheme,
} from './participantTheme.js';

describe('participantTheme storage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('defaults to system', () => {
    expect(getParticipantTheme('NC-ONE')).toBe('system');
  });

  it('persists system, light, and dark per participant', () => {
    setParticipantTheme('NC-ONE', 'light');
    setParticipantTheme('NC-TWO', 'dark');
    setParticipantTheme('NC-THREE', 'system');
    expect(getParticipantTheme('NC-ONE')).toBe('light');
    expect(getParticipantTheme('NC-TWO')).toBe('dark');
    expect(getParticipantTheme('NC-THREE')).toBe('system');
  });

  it('validates stored values and rejects unknown themes', () => {
    localStorage.setItem('nc3_participant_themes', JSON.stringify({ 'NC-ONE': 'neon' }));
    expect(getParticipantTheme('NC-ONE')).toBe('system');
    expect(normalizeParticipantTheme('purple')).toBe('system');
  });

  it('handles malformed storage safely', () => {
    localStorage.setItem('nc3_participant_themes', '{bad');
    expect(getParticipantTheme('NC-ONE')).toBe('system');
  });

  it('resolveParticipantTheme follows matchMedia for system', () => {
    vi.stubGlobal('matchMedia', vi.fn(() => ({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })));
    expect(resolveParticipantTheme('system')).toBe('light');
    expect(resolveParticipantTheme('dark')).toBe('dark');
    vi.unstubAllGlobals();
  });

  it('applySystemTheme registers and cleans up matchMedia listener', () => {
    const remove = vi.fn();
    const add = vi.fn();
    vi.stubGlobal('matchMedia', vi.fn(() => ({
      matches: true,
      addEventListener: add,
      removeEventListener: remove,
    })));
    const onChange = vi.fn();
    const cleanup = applySystemTheme(onChange);
    expect(add).toHaveBeenCalled();
    cleanup();
    expect(remove).toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
});
