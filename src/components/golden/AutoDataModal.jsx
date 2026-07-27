import { useEffect, useMemo, useState } from 'react';
import { goldenVaultApplyAutoData, goldenVaultPreviewAutoData } from '../../store/goldenVault.js';

const WEEKDAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function todayIso() {
  const d = new Date();
  const pad = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function frequencyFromRow(row) {
  return row?.autoDataFrequency || 'daily';
}

export default function AutoDataModal({ row, onClose, onApplied, busy: externalBusy }) {
  const [startDate, setStartDate] = useState(row?.autoDataStartDate || todayIso());
  const [endMode, setEndMode] = useState(row?.autoDataEndDate ? 'date' : 'never');
  const [endDate, setEndDate] = useState(row?.autoDataEndDate || startDate);
  const [frequency, setFrequency] = useState(frequencyFromRow(row));
  const [weekdays, setWeekdays] = useState(() => row?.autoDataWeekdays || [0, 2]);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const weekdayCount = useMemo(() => {
    if (frequency === 'weekly') return 1;
    if (frequency === 'twice_weekly') return 2;
    if (frequency === 'four_times_weekly') return 4;
    return 0;
  }, [frequency]);

  useEffect(() => {
    if (frequency === 'daily') return;
    setWeekdays(prev => {
      const next = [...prev];
      while (next.length < weekdayCount) next.push((next.length * 2) % 7);
      return next.slice(0, weekdayCount).sort((a, b) => a - b);
    });
  }, [frequency, weekdayCount]);

  const payload = () => ({
    start_date: startDate,
    end_date: endMode === 'never' ? null : endDate,
    frequency,
    weekdays: frequency === 'daily' ? null : weekdays,
  });

  const runPreview = async () => {
    setError('');
    setBusy(true);
    try {
      const data = await goldenVaultPreviewAutoData(row.participantId, payload());
      setPreview(data);
    } catch (err) {
      setError(err?.message || 'Preview failed');
      setPreview(null);
    } finally {
      setBusy(false);
    }
  };

  const runApply = async () => {
    setError('');
    setBusy(true);
    try {
      await goldenVaultApplyAutoData(row.participantId, payload());
      onApplied?.();
      onClose();
    } catch (err) {
      setError(err?.message || 'Apply failed');
    } finally {
      setBusy(false);
    }
  };

  const toggleWeekday = (day) => {
    if (frequency === 'daily') return;
    setWeekdays(prev => {
      if (prev.includes(day)) return prev.filter(d => d !== day);
      if (prev.length >= weekdayCount) return prev;
      return [...prev, day].sort((a, b) => a - b);
    });
  };

  const disabled = busy || externalBusy;

  return (
    <div role="dialog" aria-modal="true" data-testid="auto-data-modal" style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 70, padding: 16 }}>
      <div className="golden-vault-card" style={{ padding: 20, maxWidth: 520, width: '100%', maxHeight: '90vh', overflow: 'auto' }}>
        <h3 style={{ margin: '0 0 8px', color: '#d4af37' }}>Auto Data — {row.participantId}</h3>
        <p style={{ fontSize: 12, color: '#b8b0a0', margin: '0 0 16px' }}>Configure date-range simulated sessions (does not create real study rows).</p>

        <label style={{ display: 'block', fontSize: 12, marginBottom: 6 }}>Start date</label>
        <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} data-testid="auto-data-start" style={{ width: '100%', marginBottom: 12, padding: 8 }} />

        <fieldset style={{ border: 'none', padding: 0, marginBottom: 12 }}>
          <legend style={{ fontSize: 12, marginBottom: 6 }}>End date</legend>
          <label style={{ marginRight: 12, fontSize: 13 }}>
            <input type="radio" name="endMode" checked={endMode === 'never'} onChange={() => setEndMode('never')} /> Never
          </label>
          <label style={{ fontSize: 13 }}>
            <input type="radio" name="endMode" checked={endMode === 'date'} onChange={() => setEndMode('date')} /> Choose date
          </label>
          {endMode === 'date' && (
            <input type="date" value={endDate} min={startDate} onChange={e => setEndDate(e.target.value)} data-testid="auto-data-end" style={{ width: '100%', marginTop: 8, padding: 8 }} />
          )}
        </fieldset>

        <label style={{ display: 'block', fontSize: 12, marginBottom: 6 }}>Frequency</label>
        <select value={frequency} onChange={e => setFrequency(e.target.value)} data-testid="auto-data-frequency" style={{ width: '100%', marginBottom: 12, padding: 8 }}>
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
          <option value="twice_weekly">2 days per week</option>
          <option value="four_times_weekly">4 days per week</option>
        </select>

        {frequency !== 'daily' && (
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 12, marginBottom: 6 }}>Weekdays ({weekdays.length}/{weekdayCount})</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {WEEKDAY_LABELS.map((label, idx) => (
                <button
                  key={label}
                  type="button"
                  className="golden-vault-btn"
                  aria-pressed={weekdays.includes(idx)}
                  onClick={() => toggleWeekday(idx)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        )}

        {preview && (
          <pre data-testid="auto-data-preview" style={{ fontSize: 11, background: '#0f0f11', padding: 12, borderRadius: 8, whiteSpace: 'pre-wrap', marginBottom: 12 }}>
            {`Scheduled through today: ${preview.scheduledThroughToday}
Already generated: ${preview.alreadyGenerated}
New sessions to add: ${preview.newSessionsToAdd}
Resulting displayed sessions: ${preview.resultingDisplayedSessions}`}
          </pre>
        )}

        {error && <p role="alert" style={{ color: '#f87171', fontSize: 12 }}>{error}</p>}

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'flex-end' }}>
          <button type="button" className="golden-vault-btn" onClick={onClose} disabled={disabled}>Cancel</button>
          <button type="button" className="golden-vault-btn" onClick={runPreview} disabled={disabled}>Preview</button>
          <button type="button" className="golden-vault-btn golden-vault-btn-primary" onClick={runApply} disabled={disabled}>
            {busy ? 'Applying…' : 'Apply Auto Data'}
          </button>
        </div>
      </div>
    </div>
  );
}
