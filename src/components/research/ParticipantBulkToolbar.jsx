import { useState } from 'react';
import { T } from '../../constants/tokens.js';
import Btn from '../ui/Btn.jsx';
import {
  bulkEmailParticipants,
  bulkMessageParticipants,
  bulkReactivateParticipants,
  bulkRefreshFeedback,
  bulkReleaseFeedback,
  bulkRemoveParticipants,
  bulkRevokeFeedback,
  bulkSuspendParticipants,
  buildBulkSelectionPayload,
} from '../../store/research.js';

const MAX_BULK = 25;
const EMAIL_DISABLED_REASON = 'Email is not configured on the server.';
const GROQ_NOT_READY_REASON = 'Groq feedback is not ready. Check provider status above.';

const SUSPEND_DURATIONS = [
  ['24_hours', '24 hours'],
  ['48_hours', '48 hours'],
  ['1_week', '1 week'],
  ['1_month', '1 month'],
  ['indefinite', 'Indefinitely'],
];

function normalizeBulkResult(result) {
  if (!result || typeof result !== 'object') return null;
  return {
    requestedCount: result.requested_count ?? result.requestedCount ?? 0,
    eligibleCount: result.eligible_count ?? result.eligibleCount ?? 0,
    succeededCount: result.succeeded_count ?? result.succeededCount ?? 0,
    failedCount: result.failed_count ?? result.failedCount ?? 0,
    skippedCount: result.skipped_count ?? result.skippedCount ?? 0,
    failures: Array.isArray(result.failures) ? result.failures : [],
  };
}

function BulkResultPanel({ result, onClose }) {
  const normalized = normalizeBulkResult(result);
  if (!normalized) return null;
  const partial = normalized.failedCount > 0 || normalized.skippedCount > 0;
  return (
    <div style={{ background: T.surface, borderRadius: 10, padding: 14, marginTop: 12, border: `1px solid ${T.faint}` }}>
      <p style={{ fontSize: 13, margin: '0 0 8px', color: partial ? T.orange : T.green }}>
        {partial ? 'Bulk action completed with issues.' : 'Bulk action completed successfully.'}
      </p>
      <ul style={{ fontSize: 12, color: T.muted, margin: '0 0 12px', paddingLeft: 18, lineHeight: 1.7 }}>
        <li>Requested: {normalized.requestedCount}</li>
        <li>Succeeded: {normalized.succeededCount}</li>
        <li>Failed: {normalized.failedCount}</li>
        <li>Skipped: {normalized.skippedCount}</li>
      </ul>
      {normalized.failures.length > 0 && (
        <div style={{ maxHeight: 160, overflowY: 'auto', marginBottom: 12 }}>
          {normalized.failures.map((entry, index) => (
            <p key={`${entry.public_id || entry.publicId}-${index}`} style={{ fontSize: 11, color: T.red, margin: '0 0 4px' }}>
              {(entry.public_id || entry.publicId || 'Unknown')}: {entry.message || 'Failed'}
            </p>
          ))}
        </div>
      )}
      <Btn onClick={onClose}>Close</Btn>
    </div>
  );
}

function ModalShell({ title, children, onClose }) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
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
      onClick={onClose}
    >
      <div
        onClick={event => event.stopPropagation()}
        style={{
          width: 'min(480px, 100%)',
          background: T.card,
          border: `1px solid ${T.cardBorder}`,
          borderRadius: 12,
          padding: '18px 16px',
        }}
      >
        <h3 style={{ fontSize: 15, margin: '0 0 12px' }}>{title}</h3>
        {children}
      </div>
    </div>
  );
}

export default function ParticipantBulkToolbar({
  selectedCount,
  selectionMode,
  selectedIds,
  excludedIds,
  filters,
  groqReady,
  emailEnabled = false,
  onComplete,
  showToast,
}) {
  const [modal, setModal] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [reason, setReason] = useState('');
  const [duration, setDuration] = useState('24_hours');

  if (selectedCount <= 0) return null;

  const overLimit = selectedCount > MAX_BULK;
  const limitReason = `Select at most ${MAX_BULK} participants per bulk action.`;

  const selectionPayload = buildBulkSelectionPayload({
    selectionMode,
    selectedIds,
    excludedIds,
    filters,
  });

  const closeModal = () => {
    if (busy) return;
    setModal('');
    setError('');
    setSubject('');
    setBody('');
    setReason('');
    setResult(null);
  };

  const runBulk = async (fn, successMessage) => {
    setBusy(true);
    setError('');
    setResult(null);
    try {
      const response = await fn(selectionPayload);
      setResult(response);
      showToast?.(successMessage, 'success');
      await onComplete?.();
    } catch (err) {
      setError(err.message || 'Bulk action failed.');
    } finally {
      setBusy(false);
    }
  };

  const runMessage = async () => {
    const cleanedSubject = subject.trim();
    const cleanedBody = body.trim();
    if (!cleanedSubject || !cleanedBody) {
      setError('Subject and message are required.');
      return;
    }
    await runBulk(
      payload => bulkMessageParticipants({ ...payload, subject: cleanedSubject, body: cleanedBody }),
      'Bulk message sent.',
    );
  };

  const runEmail = async () => {
    const cleanedSubject = subject.trim();
    const cleanedBody = body.trim();
    if (!cleanedSubject || !cleanedBody) {
      setError('Subject and message are required.');
      return;
    }
    await runBulk(
      payload => bulkEmailParticipants({ ...payload, subject: cleanedSubject, body: cleanedBody }),
      'Bulk email queued.',
    );
  };

  const runSuspend = async () => {
    await runBulk(
      payload => bulkSuspendParticipants({ ...payload, duration, reason: reason.trim() || undefined }),
      'Bulk suspend completed.',
    );
  };

  const runReactivate = async () => {
    await runBulk(
      payload => bulkReactivateParticipants({ ...payload, reason: reason.trim() || undefined }),
      'Bulk reactivate completed.',
    );
  };

  const runRemove = async () => {
    const cleanedReason = reason.trim();
    if (!cleanedReason) {
      setError('A removal reason is required.');
      return;
    }
    await runBulk(
      payload => bulkRemoveParticipants({ ...payload, reason: cleanedReason }),
      'Bulk remove completed.',
    );
  };

  const runFeedback = async action => {
    const fn = action === 'release'
      ? bulkReleaseFeedback
      : action === 'revoke'
        ? bulkRevokeFeedback
        : bulkRefreshFeedback;
    const label = action === 'release' ? 'release' : action === 'revoke' ? 'revoke' : 'refresh';
    await runBulk(fn, `Bulk feedback ${label} completed.`);
  };

  const disableAction = overLimit;
  const disableFeedback = overLimit || !groqReady;

  const toolbarBtn = (label, onClick, { disabled, title } = {}) => (
    <Btn
      key={label}
      onClick={onClick}
      disabled={disabled || busy}
      title={title}
      style={{ fontSize: 11, padding: '5px 10px' }}
    >
      {label}
    </Btn>
  );

  return (
    <div
      data-testid="participant-bulk-toolbar"
      style={{
      marginBottom: 14,
      padding: '12px 14px',
      background: T.surface,
      borderRadius: 10,
      border: `1px solid ${T.faint}`,
    }}>
      <div style={{ fontSize: 12, color: T.muted, marginBottom: 10 }}>
        {selectedCount} participant{selectedCount === 1 ? '' : 's'} selected
        {overLimit && (
          <span style={{ color: T.orange, marginLeft: 8 }}>({limitReason})</span>
        )}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {toolbarBtn('Message', () => setModal('message'), { disabled: disableAction, title: disableAction ? limitReason : undefined })}
        {toolbarBtn('Email', () => setModal('email'), {
          disabled: disableAction || !emailEnabled,
          title: !emailEnabled ? EMAIL_DISABLED_REASON : disableAction ? limitReason : undefined,
        })}
        {toolbarBtn('Release Feedback', () => setModal('release-feedback'), {
          disabled: disableFeedback,
          title: overLimit ? limitReason : !groqReady ? GROQ_NOT_READY_REASON : undefined,
        })}
        {toolbarBtn('Revoke Feedback', () => setModal('revoke-feedback'), { disabled: disableAction })}
        {toolbarBtn('Refresh Feedback', () => setModal('refresh-feedback'), {
          disabled: disableFeedback,
          title: overLimit ? limitReason : !groqReady ? GROQ_NOT_READY_REASON : undefined,
        })}
        {toolbarBtn('Suspend', () => setModal('suspend'), { disabled: disableAction, title: disableAction ? limitReason : undefined })}
        {toolbarBtn('Reactivate', () => setModal('reactivate'), { disabled: disableAction, title: disableAction ? limitReason : undefined })}
        <Btn
          onClick={() => setModal('remove')}
          disabled={disableAction || busy}
          title={disableAction ? limitReason : undefined}
          style={{ fontSize: 11, padding: '5px 10px', color: T.red, borderColor: T.red }}
        >
          Remove
        </Btn>
      </div>

      {modal === 'message' && (
        <ModalShell title="Bulk message" onClose={closeModal}>
          <label style={{ display: 'block', fontSize: 12, marginBottom: 10 }}>
            Subject
            <input value={subject} onChange={e => setSubject(e.target.value)} style={{ display: 'block', width: '100%', marginTop: 4 }} />
          </label>
          <label style={{ display: 'block', fontSize: 12, marginBottom: 10 }}>
            Message
            <textarea value={body} onChange={e => setBody(e.target.value)} rows={5} style={{ display: 'block', width: '100%', marginTop: 4 }} />
          </label>
          {error && <p role="alert" style={{ color: T.red, fontSize: 12 }}>{error}</p>}
          {result && <BulkResultPanel result={result} onClose={closeModal} />}
          {!result && (
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <Btn primary disabled={busy} onClick={runMessage}>{busy ? 'Sending…' : 'Send Message'}</Btn>
              <Btn disabled={busy} onClick={closeModal}>Cancel</Btn>
            </div>
          )}
        </ModalShell>
      )}

      {modal === 'email' && (
        <ModalShell title="Bulk email" onClose={closeModal}>
          <p style={{ fontSize: 12, color: T.muted, marginTop: 0 }}>Send the same email to each selected participant.</p>
          <label style={{ display: 'block', fontSize: 12, marginBottom: 10 }}>
            Subject
            <input value={subject} onChange={e => setSubject(e.target.value)} style={{ display: 'block', width: '100%', marginTop: 4 }} />
          </label>
          <label style={{ display: 'block', fontSize: 12, marginBottom: 10 }}>
            Body
            <textarea value={body} onChange={e => setBody(e.target.value)} rows={5} style={{ display: 'block', width: '100%', marginTop: 4 }} />
          </label>
          {error && <p role="alert" style={{ color: T.red, fontSize: 12 }}>{error}</p>}
          {result && <BulkResultPanel result={result} onClose={closeModal} />}
          {!result && (
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <Btn primary disabled={busy} onClick={runEmail}>{busy ? 'Sending…' : 'Send Email'}</Btn>
              <Btn disabled={busy} onClick={closeModal}>Cancel</Btn>
            </div>
          )}
        </ModalShell>
      )}

      {modal === 'suspend' && (
        <ModalShell title="Bulk suspend" onClose={closeModal}>
          <label style={{ display: 'block', fontSize: 12, marginBottom: 10 }}>
            Duration
            <select value={duration} onChange={e => setDuration(e.target.value)} style={{ display: 'block', width: '100%', marginTop: 4 }}>
              {SUSPEND_DURATIONS.map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>
          <label style={{ display: 'block', fontSize: 12, marginBottom: 10 }}>
            Reason (optional)
            <textarea value={reason} onChange={e => setReason(e.target.value)} rows={3} style={{ display: 'block', width: '100%', marginTop: 4 }} />
          </label>
          {error && <p role="alert" style={{ color: T.red, fontSize: 12 }}>{error}</p>}
          {result && <BulkResultPanel result={result} onClose={closeModal} />}
          {!result && (
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <Btn primary disabled={busy} onClick={runSuspend}>{busy ? 'Suspending…' : 'Suspend'}</Btn>
              <Btn disabled={busy} onClick={closeModal}>Cancel</Btn>
            </div>
          )}
        </ModalShell>
      )}

      {modal === 'reactivate' && (
        <ModalShell title="Bulk reactivate" onClose={closeModal}>
          <p style={{ fontSize: 12, color: T.muted, marginTop: 0 }}>Unsuspend selected participants.</p>
          <label style={{ display: 'block', fontSize: 12, marginBottom: 10 }}>
            Reason (optional)
            <textarea value={reason} onChange={e => setReason(e.target.value)} rows={3} style={{ display: 'block', width: '100%', marginTop: 4 }} />
          </label>
          {error && <p role="alert" style={{ color: T.red, fontSize: 12 }}>{error}</p>}
          {result && <BulkResultPanel result={result} onClose={closeModal} />}
          {!result && (
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <Btn primary disabled={busy} onClick={runReactivate}>{busy ? 'Reactivating…' : 'Reactivate'}</Btn>
              <Btn disabled={busy} onClick={closeModal}>Cancel</Btn>
            </div>
          )}
        </ModalShell>
      )}

      {modal === 'remove' && (
        <ModalShell title="Bulk remove accounts" onClose={closeModal}>
          <p style={{ fontSize: 12, color: T.red, marginTop: 0 }}>This permanently removes participant access.</p>
          <label style={{ display: 'block', fontSize: 12, marginBottom: 10 }}>
            Reason
            <textarea value={reason} onChange={e => setReason(e.target.value)} rows={3} style={{ display: 'block', width: '100%', marginTop: 4 }} />
          </label>
          {error && <p role="alert" style={{ color: T.red, fontSize: 12 }}>{error}</p>}
          {result && <BulkResultPanel result={result} onClose={closeModal} />}
          {!result && (
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <Btn disabled={busy} onClick={runRemove} style={{ color: T.red, borderColor: T.red }}>
                {busy ? 'Removing…' : 'Remove Accounts'}
              </Btn>
              <Btn disabled={busy} onClick={closeModal}>Cancel</Btn>
            </div>
          )}
        </ModalShell>
      )}

      {(modal === 'release-feedback' || modal === 'revoke-feedback' || modal === 'refresh-feedback') && (
        <ModalShell
          title={
            modal === 'release-feedback'
              ? 'Release feedback for selection?'
              : modal === 'revoke-feedback'
                ? 'Revoke feedback for selection?'
                : 'Refresh feedback for selection?'
          }
          onClose={closeModal}
        >
          <p style={{ fontSize: 13, color: T.muted, marginTop: 0, lineHeight: 1.6 }}>
            {modal === 'release-feedback' && 'Participants will be able to view non-diagnostic research estimates generated from their study data.'}
            {modal === 'revoke-feedback' && 'Revoked feedback will no longer be visible to participants.'}
            {modal === 'refresh-feedback' && 'Regenerate Groq feedback from the latest study data for each selected participant.'}
          </p>
          {error && <p role="alert" style={{ color: T.red, fontSize: 12 }}>{error}</p>}
          {result && <BulkResultPanel result={result} onClose={closeModal} />}
          {!result && (
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <Btn
                primary
                disabled={busy}
                onClick={() => runFeedback(modal === 'release-feedback' ? 'release' : modal === 'revoke-feedback' ? 'revoke' : 'refresh')}
              >
                {busy ? 'Working…' : 'Confirm'}
              </Btn>
              <Btn disabled={busy} onClick={closeModal}>Cancel</Btn>
            </div>
          )}
        </ModalShell>
      )}
    </div>
  );
}
