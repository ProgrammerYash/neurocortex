const STORAGE_KEY = 'nc3_participant_themes';
const LAST_PARTICIPANT_KEY = 'nc3_participant_theme_last_id';

const LIGHT_VARS = {
  '--pt-bg': '#e8eef5',
  '--pt-surface': '#ffffff',
  '--pt-text': '#0f172a',
  '--pt-muted': '#475569',
};

const DARK_VARS = {
  '--pt-bg': '#060910',
  '--pt-surface': '#131928',
  '--pt-text': '#e2e8f0',
  '--pt-muted': '#a0aec0',
};

function readThemeMap() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function resolvePref(preference) {
  if (preference === 'light' || preference === 'dark') return preference;
  if (typeof window === 'undefined' || !window.matchMedia) return 'dark';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

/** Apply participant CSS variables to document (shell + App root). */
export function applyParticipantThemeToDocument(resolvedTheme) {
  if (typeof document === 'undefined') return;
  const vars = resolvedTheme === 'light' ? LIGHT_VARS : DARK_VARS;
  const root = document.documentElement;
  Object.entries(vars).forEach(([key, value]) => {
    root.style.setProperty(key, value);
  });
  root.dataset.participantTheme = resolvedTheme;
  if (document.body) {
    document.body.style.backgroundColor = vars['--pt-bg'];
    document.body.style.color = vars['--pt-text'];
  }
}

/** Apply participant CSS variables before React paints to avoid dark loader flash. */
export function bootstrapParticipantTheme(pathname = '') {
  if (typeof document === 'undefined') return;
  const isParticipantRoute =
    pathname.startsWith('/participant') ||
    pathname.startsWith('/join');
  if (!isParticipantRoute) return;

  const map = readThemeMap();
  let publicId = null;
  try {
    publicId = localStorage.getItem(LAST_PARTICIPANT_KEY);
  } catch {
    publicId = null;
  }
  const pref = publicId && map[publicId] ? map[publicId] : 'system';
  const resolved = resolvePref(pref);
  applyParticipantThemeToDocument(resolved);
}
