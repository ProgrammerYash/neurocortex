import { useState } from 'react';
import { T } from '../../constants/tokens.js';
import Btn from '../ui/Btn.jsx';
import {
  refreshParticipantFeedback,
  releaseParticipantFeedback,
  revokeParticipantFeedback,
} from '../../store/research.js';
import ParticipantAccountManagement, { AccountActionHistory } from './ParticipantAccountManagement.jsx';
import ParticipantMessaging from './ParticipantMessaging.jsx';
import ParticipantConsentSection from './ParticipantConsentSection.jsx';
import SyntheticDemoBadge from './SyntheticDemoBadge.jsx';

function dash(value) {
  return value === null || value === undefined || Number.isNaN(value) ? '—' : value;
}

export function formatReaction(value) {
  return dash(value) === '—' ? '—' : `${Math.round(value)} ms`;
}

export function formatScale(value) {
  return dash(value) === '—' ? '—' : `${Number(value).toFixed(1)} / 10`;
}

export function formatSleep(value) {
  return dash(value) === '—' ? '—' : `${Number(value).toFixed(1)} hrs`;
}

export function formatPercent(value) {
  return dash(value) === '—' ? '—' : `${Number(value).toFixed(1)}%`;
}

function statusColor(status) {
  if (status === 'Active') return T.green;
  if (status === 'Withdrawn' || status === 'Removed') return T.red;
  if (status === 'Suspended') return T.orange;
  if (status === 'Disabled') return T.red;
  return T.muted;
}

function feedbackStatusDisplay(detail) {
  return detail.feedbackStatus || detail.feedbackLabel || 'Not Released';
}

function ParticipantFeedbackControls({ detail, groqReady, onRefresh, showToast }) {
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const statusLabel = feedbackStatusDisplay(detail);
  const removed = detail?.isRemoved || detail?.status === 'Removed';

  const run = async (action, fn) => {
    if (busy) return;
    if (action === 'release' && !groqReady) return;
    setBusy(action);
    setError('');
    try {
      await fn(detail.participantId);
      showToast?.(
        action === 'release'
          ? 'Feedback released.'
          : action === 'refresh'
            ? 'Feedback refreshed.'
            : 'Feedback revoked.',
        'success',
      );
      if (onRefresh) await onRefresh(detail.participantId);
    } catch (err) {
      setError(err.message || 'Feedback action failed.');
    } finally {
      setBusy('');
    }
  };

  return (
    <section style={{ marginTop: 18, borderTop: `1px solid ${T.faint}`, paddingTop: 18 }}>
      <h3 style={{ fontSize: 12, color: T.muted, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>
        Groq feedback
      </h3>
      <div style={{ fontSize: 13, lineHeight: 1.9, marginBottom: 12 }}>
        <div>Feedback status: <strong>{statusLabel}</strong></div>
      </div>
      {!removed && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          <Btn
            disabled={!!busy || !groqReady}
            title={!groqReady ? 'Groq feedback is not ready.' : undefined}
            onClick={() => {
              if (!window.confirm('Release feedback for this participant?')) return;
              run('release', releaseParticipantFeedback);
            }}
          >
            {busy === 'release' ? 'Releasing…' : 'Release Feedback'}
          </Btn>
          <Btn
            disabled={!!busy || !groqReady}
            title={!groqReady ? 'Groq feedback is not ready.' : undefined}
            onClick={() => run('refresh', refreshParticipantFeedback)}
          >
            {busy === 'refresh' ? 'Refreshing…' : 'Refresh Feedback'}
          </Btn>
          <Btn
            disabled={!!busy}
            onClick={() => {
              if (!window.confirm('Revoke feedback for this participant?')) return;
              run('revoke', revokeParticipantFeedback);
            }}
          >
            {busy === 'revoke' ? 'Revoking…' : 'Revoke Feedback'}
          </Btn>
        </div>
      )}
      {error && <p role="alert" style={{ color: T.red, fontSize: 13, marginTop: 10 }}>{error}</p>}
    </section>
  );
}

export default function ParticipantDetailsPanel({
  detail,
  onClose,
  onRefresh,
  showToast,
  groqReady = false,
  managementApi = null,
  showSyntheticBadge = false,
}) {
  const [actionRefresh, setActionRefresh] = useState(0);
  if (!detail) return null;
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Participant details for ${detail.participantId}`}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(8, 12, 20, 0.72)',
        display: 'flex',
        justifyContent: 'flex-end',
        zIndex: 40,
      }}
      onClick={onClose}
    >
      <div
        onClick={event => event.stopPropagation()}
        style={{
          width: 'min(720px, 100%)',
          height: '100%',
          overflowY: 'auto',
          background: T.card,
          borderLeft: `1px solid ${T.cardBorder}`,
          padding: '20px 18px 28px',
        }}
      >
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          gap: 12,
          alignItems: 'center',
          marginBottom: 18,
          position: 'sticky',
          top: 0,
          background: T.card,
          paddingBottom: 10,
          zIndex: 1,
        }}>
          <div>
            <div style={{ fontSize: 11, color: T.muted, textTransform: 'uppercase', letterSpacing: 1 }}>Participant details</div>
            <div style={{ fontFamily: T.mono, color: T.teal, fontSize: 14, marginTop: 4, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              {detail.participantId}
              {showSyntheticBadge && detail.participantType === 'synthetic_demo' ? <SyntheticDemoBadge /> : null}
            </div>
          </div>
          <Btn onClick={onClose}>Close</Btn>
        </div>

        <section style={{ marginBottom: 18 }}>
          <h3 style={{ fontSize: 12, color: T.muted, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>Identity</h3>
          <div style={{ fontSize: 13, lineHeight: 1.9 }}>
            <div>Student name: <strong>{detail.studentName || '—'}</strong></div>
            <div>Guardian name: <strong>{detail.guardianName || '—'}</strong></div>
            <div>Grade: <strong>{detail.grade || '—'}</strong></div>
            <div>Age: <strong>{detail.ageDisplay ?? (detail.ageRange || '—')}</strong></div>
            <div>Joined: <strong>{detail.joinedDisplay || '—'}</strong></div>
            <div>Study Schedule: <strong>{detail.studyFrequencyLabel || 'Not Selected'}</strong></div>
            <div>Status: <strong style={{ color: statusColor(detail.status) }}>{detail.status}</strong></div>
          </div>
        </section>

        <section style={{ marginBottom: 18 }}>
          <h3 style={{ fontSize: 12, color: T.muted, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>Study summary</h3>
          <div style={{ fontSize: 13, lineHeight: 1.9 }}>
            <div>Sessions started: <strong>{detail.sessionsStarted ?? 0}</strong></div>
            <div>Fully completed sessions: <strong>{detail.sessionsCompleted ?? 0}</strong></div>
            <div>Last active: <strong>{detail.lastActiveDisplay || (detail.sessionsStarted ? detail.joinedDisplay : 'Never active')}</strong></div>
            <div>Average reaction time: <strong>{formatReaction(detail.averageReactionTimeMs)}</strong></div>
            <div>Average stress: <strong>{formatScale(detail.averageStress)}</strong></div>
            <div>Average fatigue: <strong>{formatScale(detail.averageFatigue)}</strong></div>
            <div>Average sleep: <strong>{formatSleep(detail.averageSleepHours)}</strong></div>
            <div>Average memory accuracy: <strong>{formatPercent(detail.averageMemoryAccuracy)}</strong></div>
          </div>
        </section>

        <section>
          <h3 style={{ fontSize: 12, color: T.muted, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>Recent session history</h3>
          {!detail.recentSessions?.length ? (
            <p style={{ color: T.muted, fontSize: 13 }}>No assessment activity recorded yet.</p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                <thead>
                  <tr style={{ color: T.muted, textAlign: 'left' }}>
                    {['Date', 'Reaction', 'Typing', 'Memory', 'Attention', 'Survey', 'Complete'].map(label => (
                      <th key={label} style={{ padding: '7px 6px', whiteSpace: 'nowrap' }}>{label}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {detail.recentSessions.map(row => (
                    <tr key={row.date} style={{ borderTop: `1px solid ${T.faint}` }}>
                      <td style={{ padding: '7px 6px', whiteSpace: 'nowrap' }}>{row.date}</td>
                      {[row.reactionCompleted, row.typingCompleted, row.memoryCompleted, row.attentionCompleted, row.surveyCompleted, row.complete].map((value, index) => (
                        <td key={index} style={{ padding: '7px 6px', color: value ? T.green : T.muted }}>
                          {value ? 'Yes' : 'No'}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <ParticipantFeedbackControls
          detail={detail}
          groqReady={groqReady}
          onRefresh={onRefresh}
          showToast={showToast}
        />

        <ParticipantAccountManagement
          detail={detail}
          onUpdated={async () => {
            if (onRefresh) await onRefresh(detail.participantId);
            setActionRefresh(value => value + 1);
          }}
        />

        <ParticipantMessaging detail={detail} showToast={showToast} />

        <ParticipantConsentSection
          detail={detail}
          showToast={showToast}
          onRefresh={onRefresh}
          consentApi={managementApi ? { fetchConsentPdf: managementApi.fetchConsentPdf, downloadConsent: managementApi.downloadConsent } : null}
        />

        <AccountActionHistory participantId={detail.participantId} refreshKey={actionRefresh} />
      </div>
    </div>
  );
}
