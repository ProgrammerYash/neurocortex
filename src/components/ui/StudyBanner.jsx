import { T } from '../../constants/tokens.js';

export default function StudyBanner({ title, message }) {
  return (
    <div
      style={{
        background: 'rgba(246,173,85,0.12)',
        border: '1px solid rgba(246,173,85,0.35)',
        borderRadius: 10,
        padding: '12px 16px',
        marginBottom: 14,
      }}
    >
      <div style={{ fontWeight: 700, color: T.orange, marginBottom: 4 }}>{title}</div>
      <div style={{ fontSize: 12, color: T.muted, lineHeight: 1.7 }}>{message}</div>
    </div>
  );
}
