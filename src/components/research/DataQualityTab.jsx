import { useEffect, useState } from 'react';
import { T } from '../../constants/tokens.js';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import {
  fetchDataQualityDashboard,
  fetchFlaggedSessions,
  fetchStudyProcedure,
  reviewDataQualityFlag,
} from '../../store/research.js';

export default function DataQualityTab() {
  const [dashboard, setDashboard] = useState(null);
  const [procedure, setProcedure] = useState(null);
  const [flagged, setFlagged] = useState([]);
  const [error, setError] = useState(null);
  const [busyFlag, setBusyFlag] = useState(null);

  async function reload() {
    const [dash, proc, flags] = await Promise.all([
      fetchDataQualityDashboard(),
      fetchStudyProcedure(),
      fetchFlaggedSessions(),
    ]);
    setDashboard(dash);
    setProcedure(proc);
    setFlagged(Array.isArray(flags) ? flags : []);
  }

  useEffect(() => {
    reload().catch(err => setError(err.message || 'Unable to load data quality dashboard'));
  }, []);

  async function handleReview(flagId, reviewStatus) {
    setBusyFlag(flagId);
    try {
      await reviewDataQualityFlag(flagId, reviewStatus);
      await reload();
    } catch (err) {
      setError(err.message || 'Review failed');
    } finally {
      setBusyFlag(null);
    }
  }

  if (error) {
    return <Card><p style={{ color: T.red }}>{error}</p></Card>;
  }
  if (!dashboard || !procedure) {
    return <Card><p style={{ color: T.muted, textAlign: 'center', padding: '2rem' }}>Loading data quality dashboard…</p></Card>;
  }

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <Card>
        <div style={{ fontWeight: 600, marginBottom: 8 }}>Active Study Procedure</div>
        <div style={{ fontSize: 13, color: T.muted, lineHeight: 1.7 }}>
          Version: {procedure.version}<br />
          Modules: {procedure.required_modules.join(' → ')}<br />
          Min sessions per participant: {procedure.min_sessions_per_participant}<br />
          Max sessions/day: {procedure.max_sessions_per_day} · Min interval: {procedure.min_minutes_between_sessions} min
        </div>
      </Card>

      <Card>
        <div style={{ fontWeight: 600, marginBottom: 8 }}>Session Summary</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, fontSize: 13 }}>
          <div>Completed: <strong>{dashboard.completed_sessions}</strong></div>
          <div>Incomplete: <strong>{dashboard.incomplete_sessions}</strong></div>
          <div>Abandoned: <strong>{dashboard.abandoned_sessions}</strong></div>
          <div>Flagged: <strong>{dashboard.flagged_sessions}</strong></div>
          <div>Unresolved critical flags: <strong>{dashboard.unresolved_critical_flags}</strong></div>
        </div>
      </Card>

      {dashboard.participants_below_minimum_sessions?.length ? (
        <Card>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Participants Below Minimum Sessions</div>
          {dashboard.participants_below_minimum_sessions.map(item => (
            <div key={item.public_id} style={{ fontSize: 13, color: T.muted, marginBottom: 4 }}>
              {item.public_id}: {item.completed_sessions}/{item.required_sessions}
            </div>
          ))}
        </Card>
      ) : null}

      {flagged.slice(0, 10).map(item => (
        <Card key={item.session_id}>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>
            {item.public_id} · {item.session_date} · {item.session_status}
          </div>
          {item.flags.map(flag => (
            <div key={flag.id} style={{ borderTop: `1px solid ${T.faint}`, paddingTop: 8, marginTop: 8 }}>
              <div style={{ fontSize: 13, color: T.muted }}>{flag.flag_type} ({flag.severity}) — {flag.reason}</div>
              <div style={{ fontSize: 12, color: T.muted, marginTop: 4 }}>Review: {flag.review_status}</div>
              <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                {['unresolved', 'reviewed_valid', 'reviewed_exclude'].map(status => (
                  <Btn
                    key={status}
                    onClick={() => handleReview(flag.id, status)}
                    style={{ fontSize: 12, padding: '6px 10px', opacity: busyFlag === flag.id ? 0.6 : 1 }}
                  >
                    {status.replace(/_/g, ' ')}
                  </Btn>
                ))}
              </div>
            </div>
          ))}
        </Card>
      ))}
    </div>
  );
}
