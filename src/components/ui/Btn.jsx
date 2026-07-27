import { useContext } from 'react';
import { T } from '../../constants/tokens.js';
import { participantTokens } from '../../constants/participantTokens.js';
import { ParticipantThemeContext } from '../participant/ParticipantAppShell.jsx';

export default function Btn({ children, onClick, primary, style, disabled, type = 'button', ...rest }) {
  const { resolvedTheme } = useContext(ParticipantThemeContext);
  const P = participantTokens(resolvedTheme || 'dark');

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      style={{
        border: primary ? 'none' : `1px solid ${P.faint}`,
        borderRadius: 9,
        padding: '9px 18px',
        fontSize: 14,
        cursor: disabled ? 'not-allowed' : 'pointer',
        background: primary ? `linear-gradient(135deg,${P.tealDim},${P.blueDim})` : P.surface,
        color: primary ? '#fff' : P.text,
        fontFamily: T.font,
        fontWeight: 500,
        opacity: disabled ? 0.5 : 1,
        transition: 'all .18s',
        ...style,
      }}
      {...rest}
    >
      {children}
    </button>
  );
}
