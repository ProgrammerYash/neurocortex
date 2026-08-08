import { useState } from 'react';
import { T } from '../../constants/tokens.js';
import Btn from '../ui/Btn.jsx';
import { downloadConsent, fetchConsentPdf } from '../../store/consent.js';
import { fixLegacyConsentSignature } from '../../store/research.js';
import { ensurePdfBlob, revokeObjectUrlLater, triggerBlobDownload } from '../../utils/blobDownload.js';

const VIEW_ERROR = 'Unable to open the consent PDF.';
const DOWNLOAD_ERROR = 'Unable to download the consent PDF.';
const POPUP_BLOCKED = 'Your browser blocked the PDF tab. Allow pop-ups for this site and try again.';

function FixLegacySignatureModal({ detail, onClose, onConfirm, busy }) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(8, 12, 20, 0.72)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 50,
        padding: 16,
      }}
    >
      <div style={{ background: T.card, borderRadius: 12, padding: 20, maxWidth: 440, width: '100%', border: `1px solid ${T.cardBorder}` }}>
        <h3 style={{ margin: '0 0 10px', fontSize: 16 }}>Fix legacy signature</h3>
        <p style={{ fontSize: 13, lineHeight: 1.6, color: T.muted, margin: '0 0 12px' }}>
          This regenerates the delivery PDF using typed cursive signatures from the stored printed names.
          The original consent record, archived PDF, signature images, and all consent timestamps remain unchanged.
        </p>
        <p style={{ fontSize: 13, margin: '0 0 16px' }}>
          Participant: <strong>{detail.participantId}</strong><br />
          Original signing date: <strong>{detail.consentStudentSignedDisplay || '—'}</strong>
        </p>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Btn onClick={onClose} disabled={busy}>Cancel</Btn>
          <Btn onClick={onConfirm} disabled={busy}>{busy ? 'Repairing consent PDF…' : 'Confirm repair'}</Btn>
        </div>
      </div>
    </div>
  );
}

export default function ParticipantConsentSection({ detail, showToast, onRefresh, consentApi = null }) {
  const [busyAction, setBusyAction] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [confirmOpen, setConfirmOpen] = useState(false);

  if (!detail) return null;

  const recorded = detail.consentRecorded && detail.consentRecordId;
  const repairEligible = detail.legacySignatureRepairEligible;
  const repaired = detail.legacySignatureRepaired;

  const fetchPdf = consentApi?.fetchConsentPdf || fetchConsentPdf;
  const downloadPdfApi = consentApi?.downloadConsent || downloadConsent;

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
        const { blob, contentType } = await fetchPdf(detail.consentRecordId);
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
      const { blob, filename, contentType } = await downloadPdfApi(detail.consentRecordId);
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

  const runRepair = async () => {
    if (busyAction) return;
    setBusyAction('repair');
    setError('');
    setSuccess('');
    try {
      await fixLegacyConsentSignature(detail.participantId);
      setSuccess('Legacy signature fixed.');
      showToast?.('Legacy signature fixed.', 'success');
      setConfirmOpen(false);
      if (onRefresh) await onRefresh(detail.participantId);
    } catch (err) {
      setError(err.message || 'Consent repair failed.');
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
            {repaired ? <div>Signature repair: <strong>Legacy signature fixed</strong></div> : null}
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <Btn disabled={!!busyAction} onClick={viewPdf}>
              {busyAction === 'view' ? 'Opening…' : 'View PDF'}
            </Btn>
            <Btn disabled={!!busyAction} onClick={downloadPdf}>
              {busyAction === 'download' ? 'Downloading…' : 'Download PDF'}
            </Btn>
            {repairEligible ? (
              <Btn disabled={!!busyAction} onClick={() => setConfirmOpen(true)}>
                Fix Legacy Signature
              </Btn>
            ) : null}
          </div>
        </>
      )}
      {success && <p style={{ color: T.green, fontSize: 13, marginTop: 10 }}>{success}</p>}
      {error && <p role="alert" style={{ color: T.red, fontSize: 13, marginTop: 10 }}>{error}</p>}
      {confirmOpen ? (
        <FixLegacySignatureModal
          detail={detail}
          busy={busyAction === 'repair'}
          onClose={() => !busyAction && setConfirmOpen(false)}
          onConfirm={runRepair}
        />
      ) : null}
    </section>
  );
}
