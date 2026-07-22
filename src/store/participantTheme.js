const STORAGE_KEY = 'nc3_participant_themes';

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

export function getParticipantTheme(publicId) {
  if (!publicId) return 'dark';
  const theme = readMap()[publicId];
  return theme === 'light' ? 'light' : 'dark';
}

export function setParticipantTheme(publicId, theme) {
  if (!publicId) return;
  const normalized = theme === 'light' ? 'light' : 'dark';
  const map = readMap();
  map[publicId] = normalized;
  writeMap(map);
}
