import { describe, expect, it } from 'vitest';
import { participantTokens } from '../../constants/participantTokens.js';
import { T } from '../../constants/tokens.js';

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
});
