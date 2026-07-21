import { useState } from 'react';
import { T } from '../../constants/tokens.js';
import Btn from '../ui/Btn.jsx';
import { downloadConsent, fetchConsentPdf } from '../../store/consent.js';

function revokeLater(url) {
  if (!url) return;
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

export default function ParticipantConsentSection({ detail, showToast }) {
  const [busyAction, setBusyAction] = useState('');
  const [error, setError] = useState('');

  if (!detail) return null;

  const recorded = detail.consentRecorded && detail.consentRecordId;

  const viewPdf = async () => {
    setBusyAction('view');
    setError('');
    try {
      const blob = await fetchConsentPdf(detail.consentRecordId);
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank', 'noopener,noreferrer');
      revokeLater(url);
    } catch (err) {
      setError(err.message || 'Could not open consent PDF.');
      showToast?.(err.message || 'Could not open consent PDF.', 'error');
    } finally {
      setBusyAction('');
    }
  };

  const downloadPdf = async () => {
    setBusyAction('download');
    setError('');
    try {
      const blob = await downloadConsent(detail.consentRecordId);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `${detail.participantId}-consent.pdf`;
      anchor.click();
      revokeLater(url);
    } catch (err) {
      setError(err.message || 'Could not download consent PDF.');
      showToast?.(err.message || 'Could not download consent PDF.', 'error');
    } finally {
      setBusyAction('');
    }
  };

  return (
    <section style={{ marginTop: 18, borderTop: `1px solid ${T.faint}`, paddingTop: 18 }}>
      <h3 style={{ fontSize: 12, color: T.muted, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>
        Consent form
      </h3>
      {!recorded ? (
        <p style={{ color: T.muted, fontSize: 13 }}>No signed consent form.</p>
      ) : (
        <>
          <div style={{ fontSize: 13, lineHeight: 1.9, marginBottom: 12 }}>
            <div>Status: <strong>Recorded</strong></div>
            <div>Student signed: <strong>{detail.consentStudentSignedDisplay || '—'}</strong></div>
            <div>Guardian signed: <strong>{detail.consentGuardianSignedDisplay || '—'}</strong></div>
            <div>Consent version: <strong>{detail.consentVersion || '—'}</strong></div>
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <Btn disabled={busyAction === 'view'} onClick={viewPdf}>
              {busyAction === 'view' ? 'Opening…' : 'View PDF'}
            </Btn>
            <Btn disabled={busyAction === 'download'} onClick={downloadPdf}>
              {busyAction === 'download' ? 'Downloading…' : 'Download PDF'}
            </Btn>
          </div>
        </>
      )}
      {error && <p role="alert" style={{ color: T.red, fontSize: 13, marginTop: 10 }}>{error}</p>}
    </section>
  );
}
