import { T } from '../../constants/tokens.js';
import InlineLoadingIndicator from './InlineLoadingIndicator.jsx';

export default function AppPageLoader({ label = 'Loading…', participant = false }) {
  const background = participant ? 'var(--pt-bg, #060910)' : T.bg;
  const color = participant ? 'var(--pt-text, #e2e8f0)' : T.text;
  const muted = participant ? 'var(--pt-muted, #a0aec0)' : T.muted;
  return (
    <div
      className={`app-page-loader${participant ? ' app-page-loader--participant' : ''}`}
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
