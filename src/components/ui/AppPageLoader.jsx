import { T } from '../../constants/tokens.js';
import InlineLoadingIndicator from './InlineLoadingIndicator.jsx';

export default function AppPageLoader({ label = 'Loading…' }) {
  const background = 'var(--pt-bg, #060910)';
  const color = 'var(--pt-text, #e2e8f0)';
  const muted = 'var(--pt-muted, #a0aec0)';
  return (
    <div
      className="app-page-loader app-page-loader--participant"
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
        background,
        color,
        fontFamily: T.font,
      }}
    >
      <InlineLoadingIndicator size={36} />
      <span style={{ fontSize: 14, color: muted }}>{label}</span>
    </div>
  );
}
