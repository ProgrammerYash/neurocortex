import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { participantTokens } from '../../constants/participantTokens.js';
import { T } from '../../constants/tokens.js';
import { bootstrapParticipantTheme } from '../../utils/bootstrapParticipantTheme.js';

const root = join(dirname(fileURLToPath(import.meta.url)), '../..');

describe('participant light theme tokens', () => {
  it('uses dark readable text on light surfaces', () => {
    const light = participantTokens('light');
    expect(light.text).not.toBe(T.text);
    expect(light.text.toLowerCase()).not.toBe('#e2e8f0');
    expect(light.muted).not.toBe(T.muted);
  });

  it('keeps dark theme tokens unchanged', () => {
    expect(participantTokens('dark')).toEqual(T);
  });

  it('defines light participant CSS variables', () => {
    const css = readFileSync(join(root, 'styles/participant-theme.css'), 'utf8');
    expect(css).toContain('.participant-app--light');
    expect(css).toContain('--pt-bg: #e8eef5');
  });

  it('bootstrapParticipantTheme sets root vars on participant paths', () => {
    localStorage.setItem('nc3_participant_themes', JSON.stringify({ DEMO123: 'light' }));
    localStorage.setItem('nc3_participant_theme_last_id', 'DEMO123');
    document.documentElement.style.removeProperty('--pt-bg');
    bootstrapParticipantTheme('/participant/dashboard');
    expect(document.documentElement.style.getPropertyValue('--pt-bg')).toBe('#e8eef5');
  });
});
