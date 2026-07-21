import { useState } from 'react';
import { T } from '../../constants/tokens.js';
import Btn from '../ui/Btn.jsx';
import { downloadConsent, fetchConsentPdf } from '../../store/consent.js';
import { ensurePdfBlob, revokeObjectUrlLater, triggerBlobDownload } from '../../utils/blobDownload.js';

const VIEW_ERROR = 'Unable to open the consent PDF.';
const DOWNLOAD_ERROR = 'Unable to download the consent PDF.';
const POPUP_BLOCKED = 'Your browser blocked the PDF tab. Allow pop-ups for this site and try again.';

export default function ParticipantConsentSection({ detail, showToast }) {
  const [busyAction, setBusyAction] = useState('');
  const [error, setError] = useState('');

  if (!detail) return null;

  const recorded = detail.consentRecorded && detail.consentRecordId;

  const viewPdf = () => {
    if (busyAction) return;
    setError('');
    const newTab = window.open('', '_blank');
    if (!newTab) {
      setError(POPUP_BLOCKED);
      showToast?.(POPUP_BLOCKED, 'error');
      return;
    }

    setBusyAction('view');
    (async () => {
      try {
        const { blob, contentType } = await fetchConsentPdf(detail.consentRecordId);
        const pdfBlob = ensurePdfBlob(blob, contentType);
        const objectUrl = URL.createObjectURL(pdfBlob);
        newTab.location.href = objectUrl;
        revokeObjectUrlLater(objectUrl);
      } catch {
        newTab.close();
        setError(VIEW_ERROR);
        showToast?.(VIEW_ERROR, 'error');
      } finally {
        setBusyAction('');
      }
    })();
  };

  const downloadPdf = async () => {
    if (busyAction) return;
    setBusyAction('download');
    setError('');
    try {
      const { blob, filename, contentType } = await downloadConsent(detail.consentRecordId);
      const pdfBlob = ensurePdfBlob(blob, contentType);
      const safeName = filename && filename !== 'consent.pdf' && filename !== 'download'
        ? filename
        : `${detail.participantId}-consent.pdf`;
      triggerBlobDownload(pdfBlob, safeName);
    } catch {
      setError(DOWNLOAD_ERROR);
      showToast?.(DOWNLOAD_ERROR, 'error');
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
            <Btn disabled={!!busyAction} onClick={viewPdf}>
              {busyAction === 'view' ? 'Opening…' : 'View PDF'}
            </Btn>
            <Btn disabled={!!busyAction} onClick={downloadPdf}>
              {busyAction === 'download' ? 'Downloading…' : 'Download PDF'}
            </Btn>
          </div>
        </>
      )}
      {error && <p role="alert" style={{ color: T.red, fontSize: 13, marginTop: 10 }}>{error}</p>}
    </section>
  );
}
