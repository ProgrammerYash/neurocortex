import { APP_THEME } from '../constants/appTheme.js';

export const PARTICIPANT_THEME_OPTIONS = ['dark'];

export function normalizeParticipantTheme() {
  return APP_THEME;
}

export function resolveParticipantTheme() {
  return APP_THEME;
}

export function applySystemTheme() {
  return () => {};
}

export function getParticipantTheme() {
  return APP_THEME;
}

export function setParticipantTheme() {
  /* dark-only: preferences ignored */
}
