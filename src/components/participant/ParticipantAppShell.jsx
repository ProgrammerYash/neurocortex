import { createContext, useContext, useEffect, useMemo } from 'react';
import { participantTokens } from '../../constants/participantTokens.js';
import { applyAppThemeToDocument } from '../../utils/bootstrapParticipantTheme.js';
import '../../styles/participant-theme.css';

const ParticipantThemeContext = createContext({
  theme: 'dark',
  resolvedTheme: 'dark',
  setTheme: () => {},
});

export { ParticipantThemeContext };

export function useParticipantTheme() {
  return useContext(ParticipantThemeContext);
}

export function useParticipantTokens() {
  return useMemo(() => participantTokens(), []);
}

export default function ParticipantAppShell({ children }) {
  useEffect(() => {
    applyAppThemeToDocument();
  }, []);

  const value = useMemo(
    () => ({
      theme: 'dark',
      resolvedTheme: 'dark',
      setTheme: () => {},
    }),
    [],
  );

  return (
    <ParticipantThemeContext.Provider value={value}>
      <div className="participant-app participant-app--dark">
        {children}
      </div>
    </ParticipantThemeContext.Provider>
  );
}
