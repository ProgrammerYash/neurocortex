import { useEffect, useMemo, useRef, useState } from 'react';
import { T } from '../../constants/tokens.js';
import {
  fetchDashboardParticipantDetail,
  fetchDashboardParticipants,
  fetchGroqProviderStatus,
} from '../../store/research.js';
import { downloadAllConsents } from '../../store/consent.js';
import { ensureZipBlob, triggerBlobDownload } from '../../utils/blobDownload.js';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';
import ParticipantBulkToolbar from './ParticipantBulkToolbar.jsx';
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
  ['ageDisplay', 'Age', 'age_display'],
  ['joinedDisplay', 'Joined', 'joined'],
  ['studyFrequencyLabel', 'Study Schedule', 'study_frequency'],
  ['sessions', 'Sessions', 'sessions'],
  ['lastActiveDisplay', 'Last Active', 'last_active'],
  ['status', 'Status', 'status'],
  ['feedbackStatus', 'AI Feedback', 'feedback_status'],
  ['averageReactionTimeMs', 'Avg Reaction', 'average_reaction_time'],
  ['averageStress', 'Avg Stress', 'average_stress'],
  ['averageFatigue', 'Avg Fatigue', 'average_fatigue'],
  ['averageSleepHours', 'Avg Sleep', 'average_sleep'],
  ['averageMemoryAccuracy', 'Avg Memory', 'average_memory_accuracy'],
  ['consentRecorded', 'Consent', 'consent'],
];

export const STATUS_FILTERS = [
  ['all_current', 'All current'],
  ['active', 'Active'],
  ['inactive', 'Inactive'],
  ['suspended', 'Suspended'],
  ['disabled', 'Disabled'],
  ['withdrawn', 'Withdrawn'],
  ['removed', 'Removed'],
];

export function emptyStateMessage(statusFilter, search) {
  if (search.trim()) return 'No participants match your search.';
  switch (statusFilter) {
    case 'active':
      return 'No active participants match this filter.';
    case 'inactive':
      return 'No inactive participants match this filter.';
    case 'suspended':
      return 'No suspended participants match this filter.';
    case 'disabled':
      return 'No disabled participants match this filter.';
    case 'withdrawn':
      return 'No withdrawn participants match this filter.';
    case 'removed':
      return 'No removed participants match this filter.';
    default:
      return 'No participants have enrolled yet.';
  }
}

function cellValue(row, key) {
  if (key === 'studentName' || key === 'guardianName') return row[key] || '—';
  if (key === 'lastActiveDisplay') return row.lastActiveDisplay || (row.sessions ? row.joinedDisplay : 'Never active');
  if (key === 'averageReactionTimeMs') return formatReaction(row.averageReactionTimeMs);
  if (key === 'averageStress') return formatScale(row.averageStress);
  if (key === 'averageFatigue') return formatScale(row.averageFatigue);
  if (key === 'averageSleepHours') return formatSleep(row.averageSleepHours);
  if (key === 'averageMemoryAccuracy') return formatPercent(row[key]);
  if (key === 'consentRecorded') return row.consentRecorded ? 'Recorded' : 'Missing';
  if (key === 'feedbackStatus') return row.feedbackStatus || 'Not Released';
  if (key === 'participantId') {
    return row.participantId;
  }
  return row[key] ?? '—';
}

function statusColor(status) {
  if (status === 'Active') return T.green;
  if (status === 'Withdrawn' || status === 'Removed' || status === 'Disabled') return T.red;
  if (status === 'Suspended') return T.orange;
  return T.muted;
}

export default function ParticipantsSection({ onSummaryRefresh, showToast, groqReady: groqReadyProp }) {
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
  const [selectedIds, setSelectedIds] = useState(() => new Set());
  const [selectAllMatching, setSelectAllMatching] = useState(false);
  const [excludedIds, setExcludedIds] = useState(() => new Set());
  const [groqReady, setGroqReady] = useState(groqReadyProp ?? false);
  const headerCheckboxRef = useRef(null);
  const limit = 20;

  useEffect(() => {
    if (groqReadyProp !== undefined) {
      setGroqReady(groqReadyProp);
      return;
    }
    fetchGroqProviderStatus()
      .then(data => setGroqReady(data.status === 'ready'))
      .catch(() => setGroqReady(false));
  }, [groqReadyProp]);

  useEffect(() => {
    const onResize = () => setCompact(window.innerWidth < 900);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  useEffect(() => {
    setSelectedIds(new Set());
    setSelectAllMatching(false);
    setExcludedIds(new Set());
  }, [search, statusFilter, sort, direction]);

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

  const pageIds = useMemo(() => items.map(row => row.participantId), [items]);

  const isRowSelected = participantId => {
    if (selectAllMatching) return !excludedIds.has(participantId);
    return selectedIds.has(participantId);
  };

  const selectedCount = selectAllMatching ? Math.max(0, total - excludedIds.size) : selectedIds.size;

  const pageSelectedCount = pageIds.filter(id => isRowSelected(id)).length;
  const allPageSelected = pageIds.length > 0 && pageSelectedCount === pageIds.length;
  const somePageSelected = pageSelectedCount > 0 && !allPageSelected;

  useEffect(() => {
    if (headerCheckboxRef.current) {
      headerCheckboxRef.current.indeterminate = somePageSelected;
    }
  }, [somePageSelected]);

  const showSelectAllBanner = allPageSelected && total > items.length && !selectAllMatching;

  const selectionMode = selectAllMatching ? 'all_matching' : 'explicit';
  const selectionFilters = useMemo(
    () => ({ search, sort, direction, status: statusFilter }),
    [search, sort, direction, statusFilter],
  );

  const clearSelection = () => {
    setSelectedIds(new Set());
    setSelectAllMatching(false);
    setExcludedIds(new Set());
  };

  const toggleRow = (participantId, event) => {
    event.stopPropagation();
    if (selectAllMatching) {
      setExcludedIds(prev => {
        const next = new Set(prev);
        if (next.has(participantId)) next.delete(participantId);
        else next.add(participantId);
        return next;
      });
      return;
    }
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(participantId)) next.delete(participantId);
      else next.add(participantId);
      return next;
    });
  };

  const togglePageSelectAll = event => {
    const checked = event.target.checked;
    if (selectAllMatching) {
      setExcludedIds(prev => {
        const next = new Set(prev);
        pageIds.forEach(id => {
          if (checked) next.delete(id);
          else next.add(id);
        });
        return next;
      });
      return;
    }
    setSelectedIds(prev => {
      const next = new Set(prev);
      pageIds.forEach(id => {
        if (checked) next.add(id);
        else next.delete(id);
      });
      return next;
    });
  };

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

  const emptyMessage = emptyStateMessage(statusFilter, search);

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

      {selectedCount > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center', marginBottom: 12 }}>
          <span style={{ fontSize: 12, color: T.muted }}>{selectedCount} selected</span>
          <Btn onClick={clearSelection} style={{ fontSize: 11, padding: '4px 10px' }}>Clear selection</Btn>
        </div>
      )}

      {showSelectAllBanner && (
        <div style={{ marginBottom: 12, padding: '10px 12px', background: 'rgba(56,189,189,0.08)', borderRadius: 8, fontSize: 12 }}>
          All {items.length} participants on this page are selected.{' '}
          <button
            type="button"
            onClick={() => {
              setSelectAllMatching(true);
              setSelectedIds(new Set());
              setExcludedIds(new Set());
            }}
            style={{ background: 'none', border: 'none', color: T.teal, cursor: 'pointer', textDecoration: 'underline', padding: 0, font: 'inherit' }}
          >
            Select all {total} matching participants
          </button>
        </div>
      )}

      <ParticipantBulkToolbar
        selectedCount={selectedCount}
        selectionMode={selectionMode}
        selectedIds={[...selectedIds]}
        excludedIds={[...excludedIds]}
        filters={selectionFilters}
        groqReady={groqReady}
        emailEnabled={false}
        onComplete={async () => {
          clearSelection();
          await load();
          if (onSummaryRefresh) await onSummaryRefresh();
        }}
        showToast={showToast}
      />

      {error && (
        <div style={{ marginBottom: 12 }}>
          <p role="alert" style={{ color: T.red, fontSize: 13, marginBottom: 8 }}>{error}</p>
          <Btn onClick={load}>Retry</Btn>
        </div>
      )}

      {loading ? (
        <p style={{ color: T.muted, padding: '24px 0', textAlign: 'center' }}>Loading participants…</p>
      ) : !total ? (
        <p style={{ color: T.muted, padding: '24px 0', textAlign: 'center' }}>{emptyMessage}</p>
      ) : !items.length ? (
        <p style={{ color: T.muted, padding: '24px 0', textAlign: 'center' }}>{emptyMessage}</p>
      ) : compact ? (
        <div style={{ display: 'grid', gap: 12 }}>
          {items.map(row => (
            <div key={row.participantId} style={{ background: T.surface, borderRadius: 10, padding: 14, border: `1px solid ${T.faint}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, marginBottom: 8, alignItems: 'start' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    aria-label={`Select ${row.participantId}`}
                    checked={isRowSelected(row.participantId)}
                    onClick={event => event.stopPropagation()}
                    onChange={event => toggleRow(row.participantId, event)}
                  />
                  <span style={{ fontFamily: T.mono, color: T.teal, fontSize: 12 }}>{row.participantId}</span>
                </label>
                <span style={{ color: statusColor(row.status), fontSize: 11 }}>{row.status}</span>
              </div>
              <div style={{ fontSize: 13, lineHeight: 1.7 }}>
                <div><strong>{row.studentName || '—'}</strong></div>
                <div style={{ color: T.muted }}>{row.guardianName || '—'}</div>
                <div>{row.grade} · {row.ageDisplay ?? row.ageRange}</div>
                <div>Sessions: {row.sessions}</div>
                <div>Last active: {row.lastActiveDisplay || (row.sessions ? row.joinedDisplay : 'Never active')}</div>
                <div>Study Schedule: {row.studyFrequencyLabel || 'Not Selected'}</div>
                <div>AI Feedback: {row.feedbackStatus || 'Not Released'}</div>
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
          <table style={{ width: '100%', minWidth: 1360, borderCollapse: 'collapse', fontSize: 11 }}>
            <thead>
              <tr>
                <th style={{ position: 'sticky', top: 0, background: T.card, zIndex: 1, padding: '8px 6px' }}>
                  <input
                    ref={headerCheckboxRef}
                    type="checkbox"
                    aria-label="Select all on page"
                    checked={allPageSelected}
                    onChange={togglePageSelectAll}
                  />
                </th>
                {COLUMNS.map(([fieldKey, label, sortKey]) => (
                  <th key={fieldKey} style={{ position: 'sticky', top: 0, background: T.card, zIndex: 1 }}>
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
                  <td style={{ padding: '8px 6px' }}>
                    <input
                      type="checkbox"
                      aria-label={`Select ${row.participantId}`}
                      checked={isRowSelected(row.participantId)}
                      onClick={event => event.stopPropagation()}
                      onChange={event => toggleRow(row.participantId, event)}
                    />
                  </td>
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

      <ParticipantDetailsPanel
        detail={detail}
        groqReady={groqReady}
        onClose={() => setDetail(null)}
        onRefresh={refreshParticipant}
        showToast={showToast}
      />
    </Card>
  );
}
