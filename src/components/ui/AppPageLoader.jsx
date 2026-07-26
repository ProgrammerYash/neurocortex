import { T } from '../../constants/tokens.js';
import InlineLoadingIndicator from './InlineLoadingIndicator.jsx';

export default function AppPageLoader({ label = 'Loading…' }) {
  return (
    <div
      className="app-page-loader"
      role="status"
      aria-live="polite"
      aria-busy="true"
      data-testid="app-page-loader"
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 16,
        background: T.bg,
        color: T.text,
        fontFamily: T.font,
      }}
    >
      <InlineLoadingIndicator size={36} />
      <span style={{ fontSize: 14, color: T.muted }}>{label}</span>
    </div>
  );
}
