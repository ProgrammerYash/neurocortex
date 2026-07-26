import { useCallback, useEffect, useMemo, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import {
  fetchGoldenVaultAuditHistory,
  fetchGoldenVaultParticipants,
  goldenVaultAdjustCoins,
  goldenVaultAdjustSessions,
  goldenVaultBulk,
  goldenVaultPatchParticipant,
  goldenVaultRegenerateFeedback,
  goldenVaultRegenerateMetrics,
  goldenVaultReleaseFeedback,
  goldenVaultResetParticipant,
  goldenVaultRevokeFeedback,
  isGoldenVaultAuthed,
  signOutGoldenVault,
} from '../../store/goldenVault.js';
import { ROUTES } from '../../routing/routePaths.js';
import '../../styles/golden-vault.css';

const PARTICLE_SEEDS = Array.from({ length: 18 }, (_, i) => ({
  id: i,
  left: `${(i * 17) % 100}%`,
  delay: `${(i * 0.7) % 8}s`,
  duration: `${10 + (i % 6)}s`,
}));

function ConfirmDialog({ title, message, onConfirm, onCancel, busy }) {
  return (
    <div role="dialog" aria-modal="true" style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 60, padding: 16 }}>
      <div className="golden-vault-card" style={{ padding: 20, maxWidth: 420, width: '100%' }}>
        <h3 style={{ margin: '0 0 10px', color: '#d4af37' }}>{title}</h3>
        <p style={{ fontSize: 13, lineHeight: 1.6, margin: '0 0 16px' }}>{message}</p>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button type="button" className="golden-vault-btn" onClick={onCancel} disabled={busy}>Cancel</button>
          <button type="button" className="golden-vault-btn golden-vault-btn-primary" onClick={onConfirm} disabled={busy}>
            {busy ? 'Working…' : 'Confirm'}
          </button>
        </div>
      </div>
    </div>
  );
}

function AmountModal({ title, onSubmit, onClose, busy }) {
  const [amount, setAmount] = useState('');
  const [error, setError] = useState('');
  const submit = () => {
    const value = Number.parseInt(amount, 10);
    if (!Number.isFinite(value) || value < 0) {
      setError('Enter a non-negative whole number.');
      return;
    }
    onSubmit(value);
  };
  return (
    <div role="dialog" aria-modal="true" style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 60, padding: 16 }}>
      <div className="golden-vault-card" style={{ padding: 20, maxWidth: 360, width: '100%' }}>
        <h3 style={{ margin: '0 0 12px', color: '#d4af37' }}>{title}</h3>
        <input
          type="number"
          min="0"
          value={amount}
          onChange={e => { setAmount(e.target.value); setError(''); }}
          style={{ width: '100%', padding: 10, borderRadius: 8, border: '1px solid rgba(212,175,55,0.4)', background: '#0f0f11', color: '#fff' }}
        />
        {error && <p role="alert" style={{ color: '#f87171', fontSize: 12, marginTop: 8 }}>{error}</p>}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 }}>
          <button type="button" className="golden-vault-btn" onClick={onClose} disabled={busy}>Cancel</button>
          <button type="button" className="golden-vault-btn golden-vault-btn-primary" onClick={submit} disabled={busy}>Apply</button>
        </div>
      </div>
    </div>
  );
}

export default function GoldenVaultPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [goldenFilter, setGoldenFilter] = useState('');
  const [feedbackFilter, setFeedbackFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [pendingKey, setPendingKey] = useState('');
  const [selected, setSelected] = useState(() => new Set());
  const [selectAllMatching, setSelectAllMatching] = useState(false);
  const [excluded, setExcluded] = useState(() => new Set());
  const [audit, setAudit] = useState([]);
  const [confirm, setConfirm] = useState(null);
  const [amountModal, setAmountModal] = useState(null);

  const authed = isGoldenVaultAuthed();
  const pageIds = useMemo(() => items.map(row => row.participantId), [items]);
  const selectedCount = selectAllMatching ? Math.max(0, total - excluded.size) : selected.size;
  const allVisibleSelected = pageIds.length > 0 && pageIds.every(id => (
    selectAllMatching ? !excluded.has(id) : selected.has(id)
  ));
  const someVisibleSelected = pageIds.some(id => (
    selectAllMatching ? !excluded.has(id) : selected.has(id)
  ));

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await fetchGoldenVaultParticipants({
        search,
        goldenEnabled: goldenFilter || undefined,
        feedbackFilter: feedbackFilter || undefined,
        limit: 50,
        offset: 0,
      });
      setItems(Array.isArray(data.items) ? data.items : []);
      setTotal(data.total ?? 0);
      const history = await fetchGoldenVaultAuditHistory();
      setAudit(Array.isArray(history) ? history : []);
    } catch (err) {
      setError(err?.message || 'Failed to load Golden Vault data.');
    } finally {
      setLoading(false);
    }
  }, [search, goldenFilter, feedbackFilter]);

  useEffect(() => {
    if (authed) load();
  }, [authed, load]);

  if (!authed) {
    return <Navigate to={ROUTES.researcherSignIn} replace />;
  }

  const runSingle = async (key, fn) => {
    if (pendingKey) return;
    setPendingKey(key);
    setMessage('');
    setError('');
    try {
      await fn();
      setMessage('Saved.');
      await load();
    } catch (err) {
      setError(err?.message || 'Action failed.');
    } finally {
      setPendingKey('');
    }
  };

  const buildSelectionPayload = () => ({
    participant_public_ids: selectAllMatching ? undefined : [...selected],
    selection_mode: selectAllMatching ? 'all_matching' : 'explicit',
    filters: {
      search,
      golden_enabled: goldenFilter || undefined,
      feedback_filter: feedbackFilter || undefined,
    },
    excluded_public_ids: selectAllMatching ? [...excluded] : undefined,
  });

  const runBulk = async (action, extra = {}) => {
    if (pendingKey || selectedCount === 0) return;
    setPendingKey(`bulk-${action}`);
    setError('');
    try {
      const result = await goldenVaultBulk({ action, ...buildSelectionPayload(), ...extra });
      setMessage(`Bulk: ${result.succeeded_count}/${result.requested_count} succeeded.`);
      await load();
    } catch (err) {
      setError(err?.message || 'Bulk action failed.');
    } finally {
      setPendingKey('');
    }
  };

  const toggleRow = (id, checked) => {
    if (selectAllMatching) {
      setExcluded(prev => {
        const next = new Set(prev);
        if (checked) next.delete(id);
        else next.add(id);
        return next;
      });
      return;
    }
    setSelected(prev => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  };

  const toggleSelectAllVisible = () => {
    if (selectAllMatching) {
      setSelectAllMatching(false);
      setExcluded(new Set());
      setSelected(new Set());
      return;
    }
    if (allVisibleSelected) {
      setSelected(new Set());
      return;
    }
    setSelected(new Set(pageIds));
  };

  const signOut = () => {
    signOutGoldenVault();
    navigate(ROUTES.researcherSignIn, { replace: true });
  };

  return (
    <div className="golden-vault-root" data-testid="golden-vault-page">
      <div className="golden-vault-particles" aria-hidden="true">
        {PARTICLE_SEEDS.map(p => (
          <span key={p.id} className="golden-vault-particle" style={{ left: p.left, animationDelay: p.delay, animationDuration: p.duration }} />
        ))}
      </div>
      <div className="golden-vault-inner">
        <header style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
          <div>
            <p style={{ margin: 0, fontSize: 12, letterSpacing: '0.2em', color: '#a89050' }}>🔒 DEMO DATA CONTROL</p>
            <h1 className="golden-vault-title">Golden Vault</h1>
            <p style={{ margin: '6px 0 0', color: '#b8b0a0' }}>Demo Data Control Center</p>
            <p style={{ margin: '10px 0 0', fontSize: 12, maxWidth: 520, lineHeight: 1.5, color: '#9a9285' }}>
              Demo overrides are active only for simulated accounts and do not create real study sessions.
            </p>
            <span className="golden-vault-badge-sim">SIMULATED DATA</span>
          </div>
          <button type="button" className="golden-vault-btn golden-vault-btn-primary" onClick={signOut}>Sign Out</button>
        </header>

        <div className="golden-vault-card" style={{ padding: 16, marginBottom: 16 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 12 }}>
            <input
              aria-label="Search participant ID"
              placeholder="Search Participant ID"
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{ flex: '1 1 180px', padding: 8, borderRadius: 8, border: '1px solid rgba(212,175,55,0.35)', background: '#0f0f11', color: '#fff' }}
            />
            <select value={goldenFilter} onChange={e => setGoldenFilter(e.target.value)} style={{ padding: 8, borderRadius: 8, background: '#0f0f11', color: '#fff', border: '1px solid rgba(212,175,55,0.35)' }}>
              <option value="">Golden: All</option>
              <option value="enabled">Golden Enabled</option>
              <option value="disabled">Golden Disabled</option>
            </select>
            <select value={feedbackFilter} onChange={e => setFeedbackFilter(e.target.value)} style={{ padding: 8, borderRadius: 8, background: '#0f0f11', color: '#fff', border: '1px solid rgba(212,175,55,0.35)' }}>
              <option value="">Feedback: All</option>
              <option value="released">Feedback Released</option>
              <option value="revoked">Feedback Revoked</option>
            </select>
            <button type="button" className="golden-vault-btn" onClick={load} disabled={loading}>Refresh</button>
          </div>

          {selectedCount > 0 && (
            <div data-testid="golden-bulk-toolbar" style={{ borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: 12, marginBottom: 8 }}>
              <p style={{ margin: '0 0 8px', fontSize: 13 }}>{selectedCount} selected</p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                <button type="button" className="golden-vault-btn" disabled={!!pendingKey} onClick={() => runBulk('enable')}>Enable Demo Override</button>
                <button type="button" className="golden-vault-btn" disabled={!!pendingKey} onClick={() => setConfirm({ title: 'Disable overrides?', message: 'Disable demo override for selected participants?', onConfirm: () => { setConfirm(null); runBulk('disable'); } })}>Disable Demo Override</button>
                <button type="button" className="golden-vault-btn" disabled={!!pendingKey} onClick={() => setAmountModal({ title: 'Add bonus sessions', onSubmit: v => { setAmountModal(null); runBulk('add_sessions', { amount: v }); } })}>Add Sessions</button>
                <button type="button" className="golden-vault-btn" disabled={!!pendingKey} onClick={() => setAmountModal({ title: 'Add bonus coins', onSubmit: v => { setAmountModal(null); runBulk('add_coins', { amount: v }); } })}>Add Coins</button>
                <button type="button" className="golden-vault-btn" disabled={!!pendingKey} onClick={() => runBulk('regenerate_metrics')}>Regenerate Demo Metrics</button>
                <button type="button" className="golden-vault-btn" disabled={!!pendingKey} onClick={() => runBulk('release_feedback')}>Release Demo Feedback</button>
                <button type="button" className="golden-vault-btn" disabled={!!pendingKey} onClick={() => runBulk('revoke_feedback')}>Revoke Demo Feedback</button>
                <button type="button" className="golden-vault-btn" disabled={!!pendingKey} onClick={() => setConfirm({ title: 'Reset all demo values?', message: 'Clears bonus sessions, coins, and simulated profile for selected accounts.', onConfirm: () => { setConfirm(null); runBulk('reset_all'); } })}>Reset All Demo Overrides</button>
                <button type="button" className="golden-vault-btn" disabled={!!pendingKey} onClick={() => { setSelectAllMatching(true); setExcluded(new Set()); setSelected(new Set()); }}>Select all matching filters</button>
                <button type="button" className="golden-vault-btn" disabled={!!pendingKey} onClick={() => { setSelected(new Set()); setExcluded(new Set()); setSelectAllMatching(false); }}>Clear selection</button>
              </div>
            </div>
          )}

          {error && <p role="alert" style={{ color: '#f87171', fontSize: 13 }}>{error}</p>}
          {message && <p style={{ color: '#86efac', fontSize: 13 }}>{message}</p>}
          {loading && <p>Loading participants…</p>}

          <div className="golden-vault-table-wrap">
            <table className="golden-vault-table">
              <thead>
                <tr>
                  <th>
                    <input
                      type="checkbox"
                      aria-label="Select all visible"
                      checked={allVisibleSelected}
                      ref={el => { if (el) el.indeterminate = someVisibleSelected && !allVisibleSelected; }}
                      onChange={toggleSelectAllVisible}
                    />
                  </th>
                  <th>Participant ID</th>
                  <th>Name</th>
                  <th>Golden</th>
                  <th>Real Sessions</th>
                  <th>Bonus</th>
                  <th>Displayed</th>
                  <th>Coins</th>
                  <th>Feedback</th>
                  <th>Updated</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map(row => {
                  const checked = selectAllMatching ? !excluded.has(row.participantId) : selected.has(row.participantId);
                  return (
                    <tr key={row.participantId}>
                      <td>
                        <input
                          type="checkbox"
                          aria-label={`Select ${row.participantId}`}
                          checked={checked}
                          onChange={e => toggleRow(row.participantId, e.target.checked)}
                        />
                      </td>
                      <td>{row.participantId}</td>
                      <td>{row.displayName || '—'}</td>
                      <td>{row.enabled ? 'Yes' : 'No'}</td>
                      <td>{row.realCompletedSessions}</td>
                      <td>{row.bonusSessions}</td>
                      <td>{row.displayedCompletedSessions}</td>
                      <td>{row.displayedCoins}</td>
                      <td>{row.feedbackLevel || '—'}</td>
                      <td>{row.updatedAt ? new Date(row.updatedAt).toLocaleString() : '—'}</td>
                      <td>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, maxWidth: 280 }}>
                          {!row.enabled ? (
                            <button type="button" className="golden-vault-btn" disabled={!!pendingKey} onClick={() => runSingle(`en-${row.participantId}`, () => goldenVaultPatchParticipant(row.participantId, { enabled: true }))}>Enable</button>
                          ) : (
                            <button type="button" className="golden-vault-btn" disabled={!!pendingKey} onClick={() => setConfirm({ title: 'Disable override?', message: `Disable demo override for ${row.participantId}?`, onConfirm: () => { setConfirm(null); runSingle(`dis-${row.participantId}`, () => goldenVaultPatchParticipant(row.participantId, { enabled: false })); } })}>Disable</button>
                          )}
                          <button type="button" className="golden-vault-btn" disabled={!!pendingKey} onClick={() => runSingle(`s1-${row.participantId}`, () => goldenVaultAdjustSessions(row.participantId, { delta: 1 }))}>+1 Ses</button>
                          <button type="button" className="golden-vault-btn" disabled={!!pendingKey} onClick={() => runSingle(`c10-${row.participantId}`, () => goldenVaultAdjustCoins(row.participantId, { delta: 10 }))}>+10 Coins</button>
                          <button type="button" className="golden-vault-btn" disabled={!!pendingKey} onClick={() => runSingle(`reg-${row.participantId}`, () => goldenVaultRegenerateMetrics(row.participantId))}>Regen Metrics</button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <section className="golden-vault-card" style={{ padding: 16 }}>
          <h2 style={{ margin: '0 0 12px', fontSize: 16, color: '#d4af37' }}>Recent Vault History</h2>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, lineHeight: 1.8, color: '#b8b0a0' }}>
            {audit.slice(0, 20).map((entry, index) => (
              <li key={`${entry.event_type}-${entry.created_at}-${index}`}>
                {entry.created_at} — {entry.event_type}
              </li>
            ))}
            {audit.length === 0 && <li>No audit events yet.</li>}
          </ul>
        </section>
      </div>

      {confirm && (
        <ConfirmDialog
          title={confirm.title}
          message={confirm.message}
          onConfirm={confirm.onConfirm}
          onCancel={() => setConfirm(null)}
          busy={!!pendingKey}
        />
      )}
      {amountModal && (
        <AmountModal
          title={amountModal.title}
          onSubmit={amountModal.onSubmit}
          onClose={() => setAmountModal(null)}
          busy={!!pendingKey}
        />
      )}
    </div>
  );
}
