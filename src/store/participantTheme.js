const STORAGE_KEY = 'nc3_participant_themes';

export const PARTICIPANT_THEME_OPTIONS = ['system', 'light', 'dark'];

function readMap() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function writeMap(map) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  } catch (error) {
    console.warn('Theme preference save failed:', error);
  }
}

export function normalizeParticipantTheme(theme) {
  if (theme === 'light' || theme === 'dark' || theme === 'system') return theme;
  if (theme === null || theme === undefined || theme === '') return 'system';
  return 'system';
}

export function resolveParticipantTheme(preference) {
  const pref = normalizeParticipantTheme(preference);
  if (pref === 'system') {
    if (typeof window === 'undefined' || !window.matchMedia) return 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  return pref;
}

export function applySystemTheme(onChange) {
  if (typeof window === 'undefined' || !window.matchMedia) {
    return () => {};
  }
  const mq = window.matchMedia('(prefers-color-scheme: dark)');
  const handler = () => onChange?.();
  mq.addEventListener('change', handler);
  return () => mq.removeEventListener('change', handler);
}

export function getParticipantTheme(publicId) {
  if (!publicId) return 'system';
  return normalizeParticipantTheme(readMap()[publicId]);
}

export function setParticipantTheme(publicId, theme) {
  if (!publicId) return;
  const normalized = normalizeParticipantTheme(theme);
  const map = readMap();
  map[publicId] = normalized;
  writeMap(map);
  try {
    localStorage.setItem('nc3_participant_theme_last_id', publicId);
  } catch {
    /* ignore */
  }
}
