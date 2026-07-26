import { T } from '../../constants/tokens.js';

export default function InlineLoadingIndicator({ size = 24, label = 'Loading' }) {
  const border = Math.max(2, Math.round(size / 12));
  return (
    <span
      className="inline-loading-indicator"
      role="status"
      aria-label={label}
      data-testid="inline-loading-indicator"
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        border: `${border}px solid rgba(255,255,255,0.12)`,
        borderTopColor: T.teal,
        display: 'inline-block',
        animation: 'spin 0.75s linear infinite',
      }}
    />
  );
}
