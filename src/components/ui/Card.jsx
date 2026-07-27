import { useContext } from 'react';
import { participantTokens } from '../../constants/participantTokens.js';
import { ParticipantThemeContext } from '../participant/ParticipantAppShell.jsx';

export default function Card({ children, style, className, ...rest }) {
  const { resolvedTheme = 'dark' } = useContext(ParticipantThemeContext);
  const P = participantTokens(resolvedTheme);
  return (
    <div
      className={className ? `participant-card ${className}` : 'participant-card'}
      style={{
        background: P.card,
        border: `1px solid ${P.cardBorder}`,
        borderRadius: 14,
        padding: '18px 20px',
        color: P.text,
        ...style,
      }}
      {...rest}
    >
      {children}
    </div>
  );
}
