import { APP_THEME, APP_THEME_CSS_VARS } from '../constants/appTheme.js';

/** Apply app dark theme CSS variables to document (shell + App root). */
export function applyAppThemeToDocument() {
  if (typeof document === 'undefined') return;
  const root = document.documentElement;
  Object.entries(APP_THEME_CSS_VARS).forEach(([key, value]) => {
    root.style.setProperty(key, value);
  });
  root.dataset.participantTheme = APP_THEME;
  root.dataset.appTheme = APP_THEME;
  if (document.body) {
    document.body.style.backgroundColor = APP_THEME_CSS_VARS['--pt-bg'];
    document.body.style.color = APP_THEME_CSS_VARS['--pt-text'];
  }
  const appRoot = document.getElementById('root');
  if (appRoot) {
    appRoot.style.minHeight = '100vh';
    appRoot.style.backgroundColor = APP_THEME_CSS_VARS['--pt-bg'];
    appRoot.style.color = APP_THEME_CSS_VARS['--pt-text'];
  }
}

/** @deprecated Use applyAppThemeToDocument */
export function applyParticipantThemeToDocument() {
  applyAppThemeToDocument();
}

/** Apply dark theme before React paints on every route. */
export function bootstrapAppTheme() {
  if (typeof document === 'undefined') return;
  applyAppThemeToDocument();
}

/** @deprecated Use bootstrapAppTheme */
export function bootstrapParticipantTheme() {
  bootstrapAppTheme();
}
