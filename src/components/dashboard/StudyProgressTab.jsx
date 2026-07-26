import { useEffect, useState } from 'react';
import { T } from '../../constants/tokens.js';
import Card from '../ui/Card.jsx';
import { fetchMyStudyProgress } from '../../store/consent.js';

function formatWeekRange(weekStart, weekEnd) {
  if (!weekStart || !weekEnd) return null;
  try {
    const start = new Date(`${weekStart}T12:00:00`);
    const end = new Date(`${weekEnd}T12:00:00`);
    const opts = { month: 'short', day: 'numeric' };
    return `${start.toLocaleDateString(undefined, opts)} – ${end.toLocaleDateString(undefined, opts)}`;
  } catch {
    return null;
  }
}

export default function StudyProgressTab() {
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    fetchMyStudyProgress()
      .then(data => { if (active) setProgress(data); })
      .catch(err => { if (active) setError(err.message || 'Unable to load study progress'); });
    return () => { active = false; };
  }, []);

  if (error) {
    return <Card><p style={{ color: T.red, fontSize: 14 }}>{error}</p></Card>;
  }
  if (!progress) {
    return <Card><p style={{ color: T.muted, textAlign: 'center', padding: '2rem' }}>Loading study progress…</p></Card>;
  }

  const weeklyTarget = progress.weekly_target;
  const weekRange = formatWeekRange(progress.week_start, progress.week_end);
  const weeklyLine = weeklyTarget != null
    ? `Completed sessions this week: ${progress.completed_this_week ?? 0} / ${weeklyTarget}`
    : null;

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <Card>
        <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 8 }}>Study Progress</div>
        {weeklyLine ? (
          <div style={{ fontSize: 13, color: T.muted, lineHeight: 1.7 }} data-testid="weekly-session-progress">
            {weeklyLine}
            {weekRange ? (
              <span style={{ display: 'block', fontSize: 12, marginTop: 4 }}>Week of {weekRange}</span>
            ) : null}
          </div>
        ) : null}
        <div style={{ fontSize: 13, color: T.muted, lineHeight: 1.7, marginTop: weeklyLine ? 8 : 0 }}>
          Completed sessions: <strong style={{ color: T.teal }}>{progress.completed_sessions}</strong> / {progress.required_sessions}
        </div>
        <div style={{ fontSize: 13, color: T.muted, marginTop: 6 }}>
          Status: <strong>{progress.study_status.replace(/_/g, ' ')}</strong>
        </div>
        <div style={{ fontSize: 13, color: T.muted, marginTop: 6 }}>
          Today&apos;s session: {progress.today_session_complete ? 'Complete' : 'Not complete'}
        </div>
        {progress.next_eligible_session_at ? (
          <div style={{ fontSize: 13, color: T.muted, marginTop: 6 }}>
            Next eligible session: {new Date(progress.next_eligible_session_at).toLocaleString()}
          </div>
        ) : null}
      </Card>

      {!progress.session_can_start && progress.session_block_message ? (
        <Card style={{ background: 'rgba(252,129,129,0.08)', border: '1px solid rgba(252,129,129,0.35)' }}>
          <div style={{ fontWeight: 600, color: T.red, marginBottom: 8 }}>Another session cannot begin yet</div>
          <div style={{ fontSize: 13, color: T.muted, lineHeight: 1.7 }}>{progress.session_block_message}</div>
        </Card>
      ) : null}
    </div>
  );
}
