/** Must stay aligned with backend/app/services/signature_style.py */
export const SIGNATURE_FONT_FAMILY = '"Dancing Script", cursive';

export const signaturePreviewStyle = {
  fontFamily: SIGNATURE_FONT_FAMILY,
  fontSize: '1.75rem',
  lineHeight: 1.2,
  margin: '12px 0 16px',
  padding: '12px 16px',
  borderRadius: 8,
  border: '1px solid var(--pt-border, rgba(99, 179, 237, 0.16))',
  background: 'var(--pt-surface-2, rgba(255,255,255,0.04))',
  color: 'var(--pt-text, inherit)',
  wordBreak: 'break-word',
};
