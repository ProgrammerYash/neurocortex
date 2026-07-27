import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import {
  applySystemTheme,
  getParticipantTheme,
  resolveParticipantTheme,
  setParticipantTheme,
  normalizeParticipantTheme,
} from '../../store/participantTheme.js';
import { participantTokens } from '../../constants/participantTokens.js';
import '../../styles/participant-theme.css';

const ParticipantThemeContext = createContext({
  theme: 'system',
  resolvedTheme: 'dark',
  setTheme: () => {},
});

export { ParticipantThemeContext };

export function useParticipantTheme() {
  return useContext(ParticipantThemeContext);
}

export function useParticipantTokens() {
  const { resolvedTheme } = useContext(ParticipantThemeContext);
  return useMemo(() => participantTokens(resolvedTheme), [resolvedTheme]);
}

export default function ParticipantAppShell({ participantId, children }) {
  const [theme, setThemeState] = useState(() => getParticipantTheme(participantId));
  const [resolvedTheme, setResolvedTheme] = useState(() =>
    resolveParticipantTheme(getParticipantTheme(participantId)),
  );

  useEffect(() => {
    const pref = getParticipantTheme(participantId);
    setThemeState(pref);
    setResolvedTheme(resolveParticipantTheme(pref));
  }, [participantId]);

  useEffect(() => {
    if (theme !== 'system') {
      setResolvedTheme(theme);
      return undefined;
    }
    setResolvedTheme(resolveParticipantTheme('system'));
    return applySystemTheme(() => setResolvedTheme(resolveParticipantTheme('system')));
  }, [theme]);

  const setTheme = next => {
    const normalized = normalizeParticipantTheme(next);
    setParticipantTheme(participantId, normalized);
    setThemeState(normalized);
  };

  const value = useMemo(
    () => ({ theme, resolvedTheme, setTheme }),
    [theme, resolvedTheme],
  );

  const modeClass = resolvedTheme === 'light' ? 'participant-app--light' : 'participant-app--dark';
  const systemClass = theme === 'system' ? 'participant-app--system' : '';

  return (
    <ParticipantThemeContext.Provider value={value}>
      <div className={`participant-app ${modeClass} ${systemClass}`.trim()}>
        {children}
      </div>
    </ParticipantThemeContext.Provider>
  );
}
