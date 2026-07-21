import { useEffect, useMemo, useState } from 'react';
import { T } from '../../constants/tokens.js';
import { fetchDashboardParticipantDetail, fetchDashboardParticipants } from '../../store/research.js';
import { downloadAllConsents } from '../../store/consent.js';
import { ensureZipBlob, triggerBlobDownload } from '../../utils/blobDownload.js';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';
import ParticipantDetailsPanel, {
  formatPercent,
  formatReaction,
  formatScale,
  formatSleep,
} from './ParticipantDetailsPanel.jsx';

const COLUMNS = [
  ['participantId', 'Participant ID', 'participant_id'],
  ['studentName', 'Student Name', 'student_name'],
  ['guardianName', 'Guardian Name', 'guardian_name'],
  ['grade', 'Grade', 'grade'],
  ['ageRange', 'Age Range', 'age_range'],
  ['joinedDisplay', 'Joined', 'joined'],
  ['sessions', 'Sessions', 'sessions'],
  ['lastActiveDisplay', 'Last Active', 'last_active'],
  ['status', 'Status', 'status'],
  ['averageReactionTimeMs', 'Avg Reaction', 'average_reaction_time'],
  ['averageStress', 'Avg Stress', 'average_stress'],
  ['averageFatigue', 'Avg Fatigue', 'average_fatigue'],
  ['averageSleepHours', 'Avg Sleep', 'average_sleep'],
  ['averageMemoryAccuracy', 'Avg Memory', 'average_memory_accuracy'],
  ['sessionCompletion', 'Session Completion', 'session_completion'],
  ['consentRecorded', 'Consent', 'consent'],
];

function cellValue(row, key) {
  if (key === 'studentName' || key === 'guardianName') return row[key] || '—';
  if (key === 'lastActiveDisplay') return row.lastActiveDisplay || (row.sessions ? row.joinedDisplay : 'Never active');
  if (key === 'averageReactionTimeMs') return formatReaction(row.averageReactionTimeMs);
  if (key === 'averageStress') return formatScale(row.averageStress);
  if (key === 'averageFatigue') return formatScale(row.averageFatigue);
  if (key === 'averageSleepHours') return formatSleep(row.averageSleepHours);
  if (key === 'averageMemoryAccuracy' || key === 'sessionCompletion') return formatPercent(row[key]);
  if (key === 'consentRecorded') return row.consentRecorded ? 'Recorded' : 'Missing';
  return row[key] ?? '—';
}

function statusColor(status) {
  if (status === 'Active') return T.green;
  if (status === 'Withdrawn' || status === 'Removed' || status === 'Disabled') return T.red;
  if (status === 'Suspended') return T.orange;
  return T.muted;
}

const STATUS_FILTERS = [
  ['all_current', 'All current'],
  ['active', 'Active'],
  ['inactive', 'Inactive'],
  ['suspended', 'Suspended'],
  ['disabled', 'Disabled'],
  ['withdrawn', 'Withdrawn'],
  ['removed', 'Removed'],
];

export default function ParticipantsSection({ onSummaryRefresh, showToast }) {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all_current');
  const [sort, setSort] = useState('joined');
  const [direction, setDirection] = useState('desc');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState('');
  const [compact, setCompact] = useState(() => typeof window !== 'undefined' && window.innerWidth < 900);
  const [zipBusy, setZipBusy] = useState(false);
  const limit = 20;

  useEffect(() => {
    const onResize = () => setCompact(window.innerWidth < 900);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const load = () => {
    setLoading(true);
    setError('');
    return fetchDashboardParticipants({ limit, offset, search, sort, direction, status: statusFilter })
      .then(data => {
        setItems(Array.isArray(data.items) ? data.items : []);
        setTotal(Number(data.total) || 0);
      })
      .catch(err => setError(err.message || 'Could not load participants.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    const timer = setTimeout(load, search ? 250 : 0);
    return () => clearTimeout(timer);
  }, [offset, search, sort, direction, statusFilter]);

  const pageLabel = useMemo(() => {
    if (!total) return '0 participants';
    return `${offset + 1}–${Math.min(offset + limit, total)} of ${total}`;
  }, [offset, total, limit]);

  const setOrdering = sortKey => {
    if (sort === sortKey) setDirection(value => (value === 'asc' ? 'desc' : 'asc'));
    else {
      setSort(sortKey);
      setDirection('asc');
    }
    setOffset(0);
  };

  const refreshParticipant = async participantId => {
    await load();
    if (detail?.participantId === participantId) {
      setDetail(await fetchDashboardParticipantDetail(participantId));
    }
    if (onSummaryRefresh) await onSummaryRefresh();
  };

  const openDetails = async participantId => {
    setDetailLoading(participantId);
    setError('');
    try {
      setDetail(await fetchDashboardParticipantDetail(participantId));
    } catch (err) {
      setError(err.message || 'Could not load participant details.');
    } finally {
      setDetailLoading('');
    }
  };

  const downloadAll = async () => {
    if (zipBusy) return;
    setZipBusy(true);
    try {
      const { blob, filename, contentType } = await downloadAllConsents();
      const zipBlob = ensureZipBlob(blob, contentType);
      const safeName = filename && filename !== 'download'
        ? filename
        : 'neurocortex-consents.zip';
      triggerBlobDownload(zipBlob, safeName);
      showToast?.('Consent archive downloaded.', 'success');
    } catch {
      showToast?.('Unable to download the consent ZIP.', 'error');
    } finally {
      setZipBusy(false);
    }
  };

  return (
    <Card className="fade-in">
      <div style={{ marginBottom: 14, display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'start', flexWrap: 'wrap' }}>
        <div>
          <SectionTitle>Participants</SectionTitle>
          <p style={{ fontSize: 12, color: T.muted, marginTop: 6 }}>
            View participant activity, assessment averages, and study progress.
          </p>
        </div>
        <Btn disabled={zipBusy} onClick={downloadAll} style={{ fontSize: 12 }}>
          {zipBusy ? 'Preparing ZIP…' : 'Download All Consent Forms'}
        </Btn>
      </div>

      <input
        aria-label="Search participants"
        placeholder="Search participant ID, student name, or guardian name…"
        value={search}
        onChange={event => {
          setSearch(event.target.value);
          setOffset(0);
        }}
        style={{ marginBottom: 12 }}
      />

      <label style={{ display: 'block', fontSize: 12, color: T.muted, marginBottom: 12 }}>
        Status filter
        <select
          aria-label="Status filter"
          value={statusFilter}
          onChange={event => {
            setStatusFilter(event.target.value);
            setOffset(0);
          }}
          style={{ display: 'block', width: '100%', marginTop: 6 }}
        >
          {STATUS_FILTERS.map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </label>

      {error && (
        <div style={{ marginBottom: 12 }}>
          <p role="alert" style={{ color: T.red, fontSize: 13, marginBottom: 8 }}>{error}</p>
          <Btn onClick={load}>Retry</Btn>
        </div>
      )}

      {loading ? (
        <p style={{ color: T.muted, padding: '24px 0', textAlign: 'center' }}>Loading participants…</p>
      ) : !total && !search.trim() ? (
        <p style={{ color: T.muted, padding: '24px 0', textAlign: 'center' }}>No participants have enrolled yet.</p>
      ) : !items.length ? (
        <p style={{ color: T.muted, padding: '24px 0', textAlign: 'center' }}>No participants match your search.</p>
      ) : compact ? (
        <div style={{ display: 'grid', gap: 12 }}>
          {items.map(row => (
            <div key={row.participantId} style={{ background: T.surface, borderRadius: 10, padding: 14, border: `1px solid ${T.faint}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, marginBottom: 8 }}>
                <div style={{ fontFamily: T.mono, color: T.teal, fontSize: 12 }}>{row.participantId}</div>
                <span style={{ color: statusColor(row.status), fontSize: 11 }}>{row.status}</span>
              </div>
              <div style={{ fontSize: 13, lineHeight: 1.7 }}>
                <div><strong>{row.studentName || '—'}</strong></div>
                <div style={{ color: T.muted }}>{row.guardianName || '—'}</div>
                <div>{row.grade} · {row.ageRange}</div>
                <div>Sessions: {row.sessions} · Completion: {formatPercent(row.sessionCompletion)}</div>
                <div>Last active: {row.lastActiveDisplay || (row.sessions ? row.joinedDisplay : 'Never active')}</div>
                <div>Consent: {row.consentRecorded ? 'Recorded' : 'Missing'}</div>
              </div>
              <Btn onClick={() => openDetails(row.participantId)} disabled={detailLoading === row.participantId} style={{ marginTop: 12, fontSize: 12 }}>
                {detailLoading === row.participantId ? 'Loading…' : 'View Details'}
              </Btn>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
          <table style={{ width: '100%', minWidth: 1320, borderCollapse: 'collapse', fontSize: 11 }}>
            <thead>
              <tr>
                {COLUMNS.map(([, label, sortKey]) => (
                  <th key={sortKey} style={{ position: 'sticky', top: 0, background: T.card, zIndex: 1 }}>
                    <button
                      onClick={() => setOrdering(sortKey)}
                      style={{ background: 'none', color: T.muted, padding: '8px 6px', whiteSpace: 'nowrap', fontWeight: 600 }}
                    >
                      {label}
                      {sort === sortKey ? direction === 'asc' ? ' ↑' : ' ↓' : ''}
                    </button>
                  </th>
                ))}
                <th style={{ color: T.muted, padding: '8px 6px' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map(row => (
                <tr key={row.participantId} style={{ borderTop: `1px solid ${T.faint}` }}>
                  {COLUMNS.map(([key]) => (
                    <td
                      key={key}
                      style={{
                        padding: '8px 6px',
                        whiteSpace: 'nowrap',
                        maxWidth: key === 'studentName' || key === 'guardianName' ? 160 : undefined,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        color: key === 'status' ? statusColor(row.status) : key === 'participantId' ? T.teal : T.text,
                        fontFamily: key === 'participantId' ? T.mono : undefined,
                      }}
                      title={key === 'studentName' || key === 'guardianName' ? row[key] || '—' : undefined}
                    >
                      {cellValue(row, key)}
                    </td>
                  ))}
                  <td style={{ padding: '8px 6px' }}>
                    <Btn onClick={() => openDetails(row.participantId)} disabled={detailLoading === row.participantId} style={{ fontSize: 11, padding: '5px 8px' }}>
                      View
                    </Btn>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 16, gap: 12, flexWrap: 'wrap' }}>
        <Btn onClick={() => setOffset(Math.max(0, offset - limit))} disabled={offset === 0 || loading}>Previous</Btn>
        <span style={{ fontSize: 12, color: T.muted }}>{pageLabel}</span>
        <Btn onClick={() => setOffset(offset + limit)} disabled={offset + limit >= total || loading}>Next</Btn>
      </div>

      <ParticipantDetailsPanel detail={detail} onClose={() => setDetail(null)} onRefresh={refreshParticipant} showToast={showToast} />
    </Card>
  );
}
