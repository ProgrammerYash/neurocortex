import { signaturePreviewStyle } from '../../constants/signatureStyle.js';

export default function TypedSignatureBlock({
  title,
  displayName,
  agreementLabel,
  agreed,
  onAgreedChange,
  testId,
}) {
  const trimmed = displayName.trim();
  return (
    <div data-testid={testId}>
      <p style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>{title}</p>
      <div className="typed-signature-preview" style={signaturePreviewStyle} aria-live="polite">
        {trimmed || '—'}
      </div>
      <label style={{ display: 'flex', gap: 10, fontSize: 13, alignItems: 'flex-start' }}>
        <input
          type="checkbox"
          checked={agreed}
          onChange={e => onAgreedChange(e.target.checked)}
          style={{ width: 'auto', marginTop: 2 }}
          disabled={!trimmed}
        />
        <span>{agreementLabel}</span>
      </label>
    </div>
  );
}
