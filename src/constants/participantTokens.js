import { T } from './tokens.js';

/** Participant dashboard palette keyed by resolved theme (light keeps readable contrast). */
export function participantTokens(resolvedTheme) {
  if (resolvedTheme === 'light') {
    return {
      ...T,
      bg: '#e8eef5',
      surface: '#f1f5f9',
      card: '#ffffff',
      cardBorder: 'rgba(15, 23, 42, 0.12)',
      glow: 'rgba(13, 148, 136, 0.08)',
      text: '#0f172a',
      muted: '#475569',
      faint: '#cbd5e1',
      teal: '#0d9488',
      tealDim: '#0f766e',
      blue: '#2563eb',
      blueDim: '#1d4ed8',
      gold: '#d97706',
      green: '#059669',
      red: '#dc2626',
    };
  }
  return T;
}
