import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { APP_THEME_CSS_VARS } from '../../constants/appTheme.js';
import { participantTokens } from '../../constants/participantTokens.js';
import { T } from '../../constants/tokens.js';
import { bootstrapAppTheme } from '../../utils/bootstrapParticipantTheme.js';

const root = join(dirname(fileURLToPath(import.meta.url)), '../..');

describe('participant dark-only theme', () => {
  it('always uses global dark tokens', () => {
    expect(participantTokens('dark')).toEqual(T);
    expect(participantTokens('light')).toEqual(T);
  });

  it('bootstrapAppTheme sets dark root vars on any path', () => {
    document.documentElement.style.removeProperty('--pt-bg');
    bootstrapAppTheme();
    expect(document.documentElement.style.getPropertyValue('--pt-bg')).toBe(APP_THEME_CSS_VARS['--pt-bg']);
    expect(document.documentElement.dataset.appTheme).toBe('dark');
  });

  it('participant shell CSS keeps dark class hooks', () => {
    const css = readFileSync(join(root, 'styles/participant-theme.css'), 'utf8');
    expect(css).toContain('.participant-app--dark');
    expect(css).toContain('--pt-bg: #060910');
  });
});
