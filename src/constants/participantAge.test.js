import { describe, expect, it } from 'vitest';
import {
  MIN_PARTICIPANT_AGE,
  MAX_PARTICIPANT_AGE,
  PARTICIPANT_AGES,
  defaultAgeConsentCategory,
  requiresAgeConsentCategory,
} from './participantAge.js';

describe('participantAge constants', () => {
  it('uses exact integer ages from 11 through max', () => {
    expect(MIN_PARTICIPANT_AGE).toBe(11);
    expect(PARTICIPANT_AGES[0]).toBe(11);
    expect(PARTICIPANT_AGES).toContain(12);
    expect(PARTICIPANT_AGES).toContain(13);
    expect(PARTICIPANT_AGES).toContain(14);
    expect(PARTICIPANT_AGES).toHaveLength(MAX_PARTICIPANT_AGE - MIN_PARTICIPANT_AGE + 1);
    expect(PARTICIPANT_AGES.at(-1)).toBe(MAX_PARTICIPANT_AGE);
    expect(PARTICIPANT_AGES).not.toContain('13-14');
    expect([...PARTICIPANT_AGES].sort((a, b) => a - b)).toEqual(PARTICIPANT_AGES);
  });

  it('maps consent categories for boundary ages', () => {
    expect(requiresAgeConsentCategory(17)).toBe(true);
    expect(requiresAgeConsentCategory(18)).toBe(true);
    expect(defaultAgeConsentCategory(13)).toBe('under_18');
    expect(defaultAgeConsentCategory(20)).toBe('age_18_or_over');
  });
});
