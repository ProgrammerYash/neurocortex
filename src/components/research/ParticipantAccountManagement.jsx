import { useEffect, useState } from 'react';
import { T } from '../../constants/tokens.js';
import Btn from '../ui/Btn.jsx';
import {
  disableParticipantAccount,
  enableParticipantAccount,
  fetchParticipantAccountActions,
  removeParticipantAccount,
  resetParticipantPin,
  suspendParticipantAccount,
  unsuspendParticipantAccount,
} from '../../store/research.js';

const DURATIONS = [
  ['24_hours', '24 hours'],
  ['48_hours', '48 hours'],
  ['1_week', '1 week'],
  ['1_month', '1 month'],
  ['indefinite', 'Indefinitely'],
];

function actionLabel(actionType) {
  return actionType.replaceAll('_', ' ');
}

export default function ParticipantAccountManagement({ detail, onUpdated }) {
  const [modal, setModal] = useState('');
  const [reason, setReason] = useState('');
  const [duration, setDuration] = useState('24_hours');
  const [confirmId, setConfirmId] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [temporaryPin, setTemporaryPin] = useState('');

  const status = detail?.status;
  const removed = status === 'Removed' || detail?.isRemoved;

  useEffect(() => {
    setTemporaryPin('');
    setModal('');
    setReason('');
    setConfirmId('');
    setError('');
  }, [detail?.participantId]);

  const runAction = async fn => {
    setBusy(true);
    setError('');
    try {
      await fn();
      setModal('');
      setReason('');
      setConfirmId('');
      await onUpdated?.();
    } catch (err) {
      setError(err.message || 'Action failed.');
    } finally {
      setBusy(false);
    }
  };

  const closeResetResult = () => {
    setTemporaryPin('');
    setModal('');
  };

  return (
    <section style={{ marginTop: 18, borderTop: `1px solid ${T.faint}`, paddingTop: 18 }}>
      <h3 style={{ fontSize: 12, color: T.muted, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>
        Account management
      </h3>

      <div style={{ fontSize: 13, lineHeight: 1.9, marginBottom: 12 }}>
        <div>Account status: <strong>{status}</strong></div>
        {detail?.isSuspended && (
          <>
            <div>Suspension reason: <strong>{detail.suspensionReason || '—'}</strong></div>
            <div>
              Suspension expiration:{' '}
              <strong>{detail.suspendedUntilDisplay || 'No automatic expiration'}</strong>
            </div>
          </>
        )}
        {detail?.isDisabled && (
          <div>Disabled reason: <strong>{detail.disabledReason || '—'}</strong></div>
        )}
        {removed && (
          <div>Removal reason: <strong>{detail.removalReason || '—'}</strong></div>
        )}
      </div>

      {!removed && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 14 }}>
          {status === 'Suspended' ? (
            <Btn onClick={() => setModal('unsuspend')}>Unsuspend</Btn>
          ) : (
            <Btn onClick={() => setModal('suspend')}>Suspend</Btn>
          )}
          <Btn onClick={() => setModal('reset')}>Reset PIN</Btn>
          {status === 'Disabled' ? (
            <Btn onClick={() => setModal('enable')}>Re-enable Account</Btn>
          ) : (
            <Btn onClick={() => setModal('disable')}>Disable Account</Btn>
          )}
          <Btn onClick={() => setModal('remove')} style={{ color: T.red, borderColor: T.red }}>
            Remove Account
          </Btn>
        </div>
      )}

      {error && (
        <p role="alert" style={{ color: T.red, fontSize: 13, marginBottom: 10 }}>{error}</p>
      )}

      {modal === 'suspend' && (
        <div style={{ background: T.surface, borderRadius: 10, padding: 14, marginBottom: 12, border: `1px solid ${T.faint}` }}>
          <LabelRow label="Duration">
            <select value={duration} onChange={e => setDuration(e.target.value)} style={{ width: '100%' }}>
              {DURATIONS.map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </LabelRow>
          <LabelRow label="Reason">
            <textarea value={reason} onChange={e => setReason(e.target.value)} rows={3} style={{ width: '100%' }} />
          </LabelRow>
          <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
            <Btn
              primary
              disabled={busy || reason.trim().length < 3}
              onClick={() => runAction(() => suspendParticipantAccount(detail.participantId, { duration, reason: reason.trim() }))}
            >
              {busy ? 'Suspending…' : 'Confirm suspend'}
            </Btn>
            <Btn onClick={() => setModal('')}>Cancel</Btn>
          </div>
        </div>
      )}

      {modal === 'unsuspend' && (
        <ModalReason
          title="Unsuspend account"
          reason={reason}
          setReason={setReason}
          busy={busy}
          onCancel={() => setModal('')}
          onConfirm={() => runAction(() => unsuspendParticipantAccount(detail.participantId, { reason: reason.trim() }))}
          confirmLabel="Confirm unsuspend"
        />
      )}

      {modal === 'disable' && (
        <ModalReason
          title="Disable account"
          warning="The participant will not be able to sign in until re-enabled."
          reason={reason}
          setReason={setReason}
          busy={busy}
          onCancel={() => setModal('')}
          onConfirm={() => runAction(() => disableParticipantAccount(detail.participantId, { reason: reason.trim() }))}
          confirmLabel="Disable account"
        />
      )}

      {modal === 'enable' && (
        <ModalReason
          title="Re-enable account"
          reason={reason}
          setReason={setReason}
          busy={busy}
          onCancel={() => setModal('')}
          onConfirm={() => runAction(() => enableParticipantAccount(detail.participantId, { reason: reason.trim() }))}
          confirmLabel="Re-enable account"
        />
      )}

      {modal === 'reset' && !temporaryPin && (
        <div style={{ background: T.surface, borderRadius: 10, padding: 14, marginBottom: 12, border: `1px solid ${T.faint}` }}>
          <p style={{ fontSize: 13, marginBottom: 10 }}>Generate a new temporary PIN for this participant?</p>
          <div style={{ display: 'flex', gap: 8 }}>
            <Btn
              primary
              disabled={busy}
              onClick={() => runAction(async () => {
                const result = await resetParticipantPin(detail.participantId);
                setTemporaryPin(result.temporaryPin || '');
              })}
            >
              {busy ? 'Resetting…' : 'Reset PIN'}
            </Btn>
            <Btn onClick={() => setModal('')}>Cancel</Btn>
          </div>
        </div>
      )}

      {temporaryPin && (
        <div style={{ background: 'rgba(167,139,250,0.12)', border: `1px solid ${T.purple}`, borderRadius: 10, padding: 14, marginBottom: 12 }}>
          <p style={{ color: T.gold, fontSize: 13, marginBottom: 8 }}>
            Copy this PIN now. It will not be shown again.
          </p>
          <input readOnly value={temporaryPin} aria-label="Temporary PIN" style={{ fontFamily: T.mono, fontSize: 18, letterSpacing: 4, width: '100%', marginBottom: 10 }} />
          <Btn onClick={closeResetResult}>Close</Btn>
        </div>
      )}

      {modal === 'remove' && (
        <div style={{ background: 'rgba(252,129,129,0.08)', border: `1px solid ${T.red}`, borderRadius: 10, padding: 14, marginBottom: 12 }}>
          <p style={{ color: T.red, fontSize: 13, marginBottom: 10 }}>
            This permanently removes login access. Research and consent records are preserved.
          </p>
          <LabelRow label="Reason">
            <textarea value={reason} onChange={e => setReason(e.target.value)} rows={3} style={{ width: '100%' }} />
          </LabelRow>
          <LabelRow label={`Type ${detail.participantId} to confirm`}>
            <input value={confirmId} onChange={e => setConfirmId(e.target.value.toUpperCase())} style={{ width: '100%', fontFamily: T.mono }} />
          </LabelRow>
          <Btn
            disabled={busy || reason.trim().length < 3 || confirmId !== detail.participantId}
            onClick={() => runAction(() => removeParticipantAccount(detail.participantId, {
              reason: reason.trim(),
              confirmationPublicId: confirmId,
            }))}
            style={{ color: T.red, borderColor: T.red, marginTop: 10 }}
          >
            {busy ? 'Removing…' : 'Remove account access'}
          </Btn>
        </div>
      )}

    </section>
  );
}

export function AccountActionHistory({ participantId, refreshKey = 0 }) {
  const [actions, setActions] = useState([]);
  const [loadingActions, setLoadingActions] = useState(true);

  useEffect(() => {
    if (!participantId) return undefined;
    setLoadingActions(true);
    fetchParticipantAccountActions(participantId)
      .then(data => setActions(Array.isArray(data.items) ? data.items : []))
      .catch(() => setActions([]))
      .finally(() => setLoadingActions(false));
  }, [participantId, refreshKey]);

  return (
    <section style={{ marginTop: 18, borderTop: `1px solid ${T.faint}`, paddingTop: 18 }}>
      <h3 style={{ fontSize: 12, color: T.muted, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>
        Account action history
      </h3>
      {loadingActions ? (
        <p style={{ color: T.muted, fontSize: 13 }}>Loading action history…</p>
      ) : !actions.length ? (
        <p style={{ color: T.muted, fontSize: 13 }}>No account actions recorded yet.</p>
      ) : (
        <div style={{ display: 'grid', gap: 8 }}>
          {actions.map(item => (
            <div key={item.id} style={{ background: T.surface, borderRadius: 8, padding: 10, border: `1px solid ${T.faint}`, fontSize: 12, lineHeight: 1.7 }}>
              <div><strong>{actionLabel(item.actionType)}</strong></div>
              <div style={{ color: T.muted }}>{item.createdAtDisplay || item.createdAt}</div>
              <div>Reason: {item.reason}</div>
              {item.durationCode && <div>Duration: {item.durationCode.replaceAll('_', ' ')}</div>}
              {item.researcherDisplayName && <div>Researcher: {item.researcherDisplayName}</div>}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function LabelRow({ label, children }) {
  return (
    <label style={{ display: 'block', marginBottom: 10 }}>
      <div style={{ fontSize: 11, color: T.muted, marginBottom: 4 }}>{label}</div>
      {children}
    </label>
  );
}

function ModalReason({ title, warning, reason, setReason, busy, onCancel, onConfirm, confirmLabel }) {
  return (
    <div style={{ background: T.surface, borderRadius: 10, padding: 14, marginBottom: 12, border: `1px solid ${T.faint}` }}>
      <div style={{ fontWeight: 600, marginBottom: 8 }}>{title}</div>
      {warning && <p style={{ fontSize: 13, color: T.muted, marginBottom: 8 }}>{warning}</p>}
      <textarea value={reason} onChange={e => setReason(e.target.value)} rows={3} style={{ width: '100%' }} placeholder="Reason" />
      <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
        <Btn primary disabled={busy || reason.trim().length < 3} onClick={onConfirm}>{busy ? 'Saving…' : confirmLabel}</Btn>
        <Btn onClick={onCancel}>Cancel</Btn>
      </div>
    </div>
  );
}
