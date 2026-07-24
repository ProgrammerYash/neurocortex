export const MIN_PARTICIPANT_AGE = 11;
export const MAX_PARTICIPANT_AGE = 26;

export const PARTICIPANT_AGES = Array.from(
  { length: MAX_PARTICIPANT_AGE - MIN_PARTICIPANT_AGE + 1 },
  (_, index) => MIN_PARTICIPANT_AGE + index,
);

export function requiresAgeConsentCategory(age) {
  return age === 17 || age === 18;
}

export function defaultAgeConsentCategory(age) {
  if (age <= 16) return 'under_18';
  if (age >= 19) return 'age_18_or_over';
  return '';
}
