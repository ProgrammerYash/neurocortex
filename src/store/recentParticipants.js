const STORAGE_KEY = 'nc3_recent_participants';
const MAX_RECENT = 20;
export const RECENT_PARTICIPANTS_EVENT = 'nc3-recent-participants-changed';

function readRaw() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeRaw(entries) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
    window.dispatchEvent(new CustomEvent(RECENT_PARTICIPANTS_EVENT));
  } catch (error) {
    console.warn('Recent participants save failed:', error);
  }
}

function normalizeEntry(entry) {
  if (!entry || typeof entry !== 'object') return null;
  const id = typeof entry.id === 'string' ? entry.id.trim().toUpperCase() : '';
  if (!id || id === 'RESEARCHER') return null;
  return {
    id,
    grade: entry.grade ?? null,
    ageRange: entry.ageRange ?? entry.age_range ?? null,
    role: entry.role === 'researcher' ? 'researcher' : 'participant',
  };
}

function dedupeEntries(entries) {
  const seen = new Set();
  const out = [];
  entries.forEach(entry => {
    const normalized = normalizeEntry(entry);
    if (!normalized || normalized.role === 'researcher' || seen.has(normalized.id)) return;
    seen.add(normalized.id);
    out.push(normalized);
  });
  return out.slice(-MAX_RECENT);
}

export function getRecentParticipants() {
  return dedupeEntries(readRaw());
}

export function replaceRecentParticipants(entries) {
  writeRaw(dedupeEntries(entries));
}

export function addRecentParticipant(profile) {
  const normalized = normalizeEntry(profile);
  if (!normalized || normalized.role === 'researcher') return;
  const rest = getRecentParticipants().filter(p => p.id !== normalized.id);
  writeRaw([...rest, normalized].slice(-MAX_RECENT));
}

export function removeRecentParticipant(publicId) {
  const id = publicId?.trim().toUpperCase();
  if (!id) return;
  const next = getRecentParticipants().filter(p => p.id !== id);
  writeRaw(next);
}

export function pruneRecentParticipants(validIds) {
  const allowed = new Set(validIds.map(v => v.trim().toUpperCase()));
  writeRaw(getRecentParticipants().filter(p => allowed.has(p.id)));
}

export function migrateRecentFromLegacyIndex(legacyIds, getProfile) {
  if (getRecentParticipants().length > 0) return;
  const entries = [];
  legacyIds.forEach(id => {
    const profile = getProfile?.(id);
    if (profile) entries.push(profile);
  });
  if (entries.length) replaceRecentParticipants(entries);
}
