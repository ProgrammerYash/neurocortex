import { useEffect, useMemo, useState } from 'react';
import {
  goldenVaultFakeUsersGenerate,
  goldenVaultFakeUsersPreview,
  goldenVaultFakeUsersProcessBatch,
  goldenVaultFakeUsersBatchStatus,
  goldenVaultFakeUsersClaimCredentials,
} from '../../store/goldenVault.js';

function todayIso() {
  const d = new Date();
  const pad = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function downloadCredentialsCsv(credentials, batchId) {
  const lines = ['participant_id,temporary_pin'];
  credentials.forEach(row => {
    lines.push(`${row.publicId},${row.temporaryPin}`);
  });
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `golden-fake-users-${batchId.slice(0, 8)}.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function FakeUsersModal({ onClose, onBatchReady }) {
  const [step, setStep] = useState('configure');
  const [total, setTotal] = useState('10');
  const [startDate, setStartDate] = useState('2026-01-15');
  const [daily, setDaily] = useState('3');
  const [weekly, setWeekly] = useState('2');
  const [twoDays, setTwoDays] = useState('3');
  const [fourDays, setFourDays] = useState('2');
  const [error, setError] = useState('');
  const [preview, setPreview] = useState(null);
  const [batchId, setBatchId] = useState('');
  const [progress, setProgress] = useState(null);
  const [credentials, setCredentials] = useState(null);
  const [busy, setBusy] = useState(false);

  const parsedTotal = Number.parseInt(total, 10) || 0;
  const distributionSum = useMemo(() => {
    const values = [daily, weekly, twoDays, fourDays].map(v => Number.parseInt(v, 10) || 0);
    return values.reduce((a, b) => a + b, 0);
  }, [daily, weekly, twoDays, fourDays]);
  const remaining = parsedTotal - distributionSum;

  const payload = () => ({
    total: parsedTotal,
    start_date: startDate,
    daily: Number.parseInt(daily, 10) || 0,
    weekly: Number.parseInt(weekly, 10) || 0,
    two_days: Number.parseInt(twoDays, 10) || 0,
    four_days: Number.parseInt(fourDays, 10) || 0,
  });

  const validateConfigure = () => {
    if (parsedTotal < 1) {
      setError('Enter at least one user.');
      return false;
    }
    if (remaining !== 0) {
      setError(`Schedule counts must add up to ${parsedTotal} (remaining ${remaining}).`);
      return false;
    }
    setError('');
    return true;
  };

  const runPreview = async () => {
    if (!validateConfigure()) return;
    setBusy(true);
    setError('');
    try {
      const data = await goldenVaultFakeUsersPreview(payload());
      setPreview(data);
      setStep('preview');
    } catch (err) {
      setError(err?.message || 'Preview failed');
    } finally {
      setBusy(false);
    }
  };

  const runGenerate = async () => {
    setBusy(true);
    setError('');
    try {
      const idempotencyKey = typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : `fake-${Date.now()}`;
      const created = await goldenVaultFakeUsersGenerate({ ...payload(), idempotency_key: idempotencyKey });
      setBatchId(created.batchId);
      setProgress(created);
      setStep('progress');
      await pumpBatch(created.batchId);
    } catch (err) {
      setError(err?.message || 'Could not start batch');
    } finally {
      setBusy(false);
    }
  };

  const pumpBatch = async (id) => {
    let done = false;
    while (!done) {
      const chunk = await goldenVaultFakeUsersProcessBatch(id);
      setProgress(chunk);
      done = chunk.status === 'completed' || chunk.status === 'completed_with_errors' || chunk.status === 'failed';
      if (!done) {
        await new Promise(resolve => setTimeout(resolve, 120));
      }
    }
    const status = await goldenVaultFakeUsersBatchStatus(id);
    setProgress(status);
    onBatchReady?.(id);
    if (status.credentialsAvailable) {
      try {
        const creds = await goldenVaultFakeUsersClaimCredentials(id);
        setCredentials(creds.credentials);
      } catch (err) {
        setError(err?.message || 'Could not retrieve credentials');
      }
    }
    setStep('results');
  };

  useEffect(() => {
    if (step !== 'progress' || !batchId) return undefined;
    return undefined;
  }, [step, batchId]);

  return (
    <div role="dialog" aria-modal="true" className="golden-vault-fake-users-modal">
      <div className="golden-vault-card golden-vault-fake-users-modal__panel">
        <header className="golden-vault-fake-users-modal__header">
          <h2>Generate Fake Users</h2>
          <button type="button" className="golden-vault-btn" onClick={onClose} disabled={busy && step === 'progress'}>
            Close
          </button>
        </header>

        {step === 'configure' && (
          <div className="golden-vault-fake-users-modal__body">
            <p className="golden-vault-fake-users-modal__lead">
              Create synthetic demo participants with typed consent PDFs, auto data, and one-time PINs. No real sessions or Groq calls.
            </p>
            <label className="golden-vault-fake-users-field">
              <span>Total users</span>
              <input type="number" min="1" max="500" value={total} onChange={e => setTotal(e.target.value)} />
            </label>
            <label className="golden-vault-fake-users-field">
              <span>Auto Data start date</span>
              <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} />
            </label>
            <div className="golden-vault-fake-users-grid">
              {[
                ['Daily', daily, setDaily],
                ['Weekly', weekly, setWeekly],
                ['2 days / week', twoDays, setTwoDays],
                ['4 days / week', fourDays, setFourDays],
              ].map(([label, value, setter]) => (
                <label key={label} className="golden-vault-fake-users-field">
                  <span>{label}</span>
                  <input type="number" min="0" value={value} onChange={e => setter(e.target.value)} />
                </label>
              ))}
            </div>
            <p className={`golden-vault-fake-users-remaining${remaining === 0 ? ' is-valid' : ''}`}>
              Remaining to assign: {remaining}
            </p>
            {error && <p role="alert" className="golden-vault-fake-users-error">{error}</p>}
            <div className="golden-vault-fake-users-actions">
              <button type="button" className="golden-vault-btn golden-vault-btn-primary" disabled={busy} onClick={runPreview}>
                Preview
              </button>
            </div>
          </div>
        )}

        {step === 'preview' && preview && (
          <div className="golden-vault-fake-users-modal__body">
            <ul className="golden-vault-fake-users-summary">
              <li>{preview.totalUsers} participants</li>
              <li>Start {preview.startDate}</li>
              <li>~{preview.estimatedAutoDataEvents} auto data events</li>
              <li>{preview.estimatedPdfCount} synthetic consent PDFs</li>
              <li>{preview.estimatedGenerationBatches} processing batches</li>
            </ul>
            {error && <p role="alert" className="golden-vault-fake-users-error">{error}</p>}
            <div className="golden-vault-fake-users-actions">
              <button type="button" className="golden-vault-btn" disabled={busy} onClick={() => setStep('configure')}>Back</button>
              <button type="button" className="golden-vault-btn golden-vault-btn-primary" disabled={busy} onClick={runGenerate}>
                {busy ? 'Starting…' : 'Generate'}
              </button>
            </div>
          </div>
        )}

        {step === 'progress' && progress && (
          <div className="golden-vault-fake-users-modal__body">
            <p>Status: {progress.status}</p>
            <p>
              Processed {progress.processedCount ?? progress.processed_count ?? 0} / {parsedTotal}
              {' '}
              (success {progress.successfulCount ?? progress.successful_count ?? 0},
              failed {progress.failedCount ?? progress.failed_count ?? 0})
            </p>
            <div className="golden-vault-fake-users-progress" aria-hidden="true">
              <div
                style={{
                  width: `${Math.min(100, ((progress.processedCount ?? 0) / Math.max(parsedTotal, 1)) * 100)}%`,
                }}
              />
            </div>
            <p className="golden-vault-fake-users-modal__lead">Do not close until generation finishes.</p>
          </div>
        )}

        {step === 'results' && progress && (
          <div className="golden-vault-fake-users-modal__body">
            <p>
              Finished with status <strong>{progress.status}</strong>.
              {' '}
              Created {progress.successfulCount ?? 0} accounts
              {(progress.failedCount ?? 0) > 0 ? ` (${progress.failedCount} failures)` : ''}.
            </p>
            {(progress.errors?.length ?? 0) > 0 && (
              <details>
                <summary>Partial failures</summary>
                <ul>
                  {progress.errors.map(err => (
                    <li key={err}>{err}</li>
                  ))}
                </ul>
              </details>
            )}
            {credentials?.length > 0 && (
              <>
                <p className="golden-vault-fake-users-warning">
                  One-time PINs — copy or download now. They cannot be retrieved again.
                </p>
                <div className="golden-vault-fake-users-credentials">
                  <table>
                    <thead>
                      <tr>
                        <th>Participant ID</th>
                        <th>Temporary PIN</th>
                      </tr>
                    </thead>
                    <tbody>
                      {credentials.map(row => (
                        <tr key={row.publicId}>
                          <td>{row.publicId}</td>
                          <td>{row.temporaryPin}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <button
                  type="button"
                  className="golden-vault-btn golden-vault-btn-primary"
                  onClick={() => downloadCredentialsCsv(credentials, batchId)}
                >
                  Download CSV
                </button>
              </>
            )}
            {error && <p role="alert" className="golden-vault-fake-users-error">{error}</p>}
            <div className="golden-vault-fake-users-actions">
              <button type="button" className="golden-vault-btn golden-vault-btn-primary" onClick={onClose}>Done</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
