import { T } from '../../constants/tokens.js';
import Btn from '../ui/Btn.jsx';

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

import ParticipantAccountManagement from './ParticipantAccountManagement.jsx';

function statusColor(status) {
  if (status === 'Active') return T.green;
  if (status === 'Withdrawn' || status === 'Removed') return T.red;
  if (status === 'Suspended') return T.orange;
  if (status === 'Disabled') return T.red;
  return T.muted;
}

export default function ParticipantDetailsPanel({ detail, onClose, onRefresh }) {
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
          width: 'min(520px, 100%)',
          height: '100%',
          overflowY: 'auto',
          background: T.card,
          borderLeft: `1px solid ${T.cardBorder}`,
          padding: '20px 18px 28px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', marginBottom: 18 }}>
          <div>
            <div style={{ fontSize: 11, color: T.muted, textTransform: 'uppercase', letterSpacing: 1 }}>Participant details</div>
            <div style={{ fontFamily: T.mono, color: T.teal, fontSize: 14, marginTop: 4 }}>{detail.participantId}</div>
          </div>
          <Btn onClick={onClose}>Close</Btn>
        </div>

        <section style={{ marginBottom: 18 }}>
          <h3 style={{ fontSize: 12, color: T.muted, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>Identity</h3>
          <div style={{ fontSize: 13, lineHeight: 1.9 }}>
            <div>Student name: <strong>{detail.studentName || '—'}</strong></div>
            <div>Guardian name: <strong>{detail.guardianName || '—'}</strong></div>
            <div>Grade: <strong>{detail.grade || '—'}</strong></div>
            <div>Age range: <strong>{detail.ageRange || '—'}</strong></div>
            <div>Joined: <strong>{detail.joinedDisplay || '—'}</strong></div>
            <div>Status: <strong style={{ color: statusColor(detail.status) }}>{detail.status}</strong></div>
          </div>
        </section>

        <section style={{ marginBottom: 18 }}>
          <h3 style={{ fontSize: 12, color: T.muted, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>Study summary</h3>
          <div style={{ fontSize: 13, lineHeight: 1.9 }}>
            <div>Sessions started: <strong>{detail.sessionsStarted ?? 0}</strong></div>
            <div>Fully completed sessions: <strong>{detail.sessionsCompleted ?? 0}</strong></div>
            <div>Session completion: <strong>{formatPercent(detail.sessionCompletion)}</strong></div>
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

        <ParticipantAccountManagement
          detail={detail}
          onUpdated={async () => {
            if (onRefresh) await onRefresh(detail.participantId);
          }}
        />
      </div>
    </div>
  );
}
