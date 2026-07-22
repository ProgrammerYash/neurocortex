import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { getParticipantTheme, setParticipantTheme } from '../../store/participantTheme.js';
import '../../styles/participant-theme.css';

const ParticipantThemeContext = createContext({
  theme: 'dark',
  setTheme: () => {},
});

export function useParticipantTheme() {
  return useContext(ParticipantThemeContext);
}

export default function ParticipantAppShell({ participantId, children }) {
  const [theme, setThemeState] = useState(() => getParticipantTheme(participantId));

  useEffect(() => {
    setThemeState(getParticipantTheme(participantId));
  }, [participantId]);

  const setTheme = next => {
    const normalized = next === 'light' ? 'light' : 'dark';
    setParticipantTheme(participantId, normalized);
    setThemeState(normalized);
  };

  const value = useMemo(() => ({ theme, setTheme }), [theme]);

  return (
    <ParticipantThemeContext.Provider value={value}>
      <div className={`participant-app participant-app--${theme}`}>
        {children}
      </div>
    </ParticipantThemeContext.Provider>
  );
}
