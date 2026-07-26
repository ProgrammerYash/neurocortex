import { useEffect, useState } from 'react';
import { T } from '../../constants/tokens.js';
import { fetchGroqProviderStatus } from '../../store/research.js';
import Btn from '../ui/Btn.jsx';
import Card from '../ui/Card.jsx';

function statusLabel(status) {
  if (status === 'ready') return 'Ready';
  if (status === 'temporarily_unavailable') return 'Temporarily Unavailable';
  return 'Not Configured';
}

function statusColor(status) {
  if (status === 'ready') return T.green;
  if (status === 'temporarily_unavailable') return T.orange;
  return T.muted;
}

export default function GroqFeedbackStatus({
  initialStatus,
  initialConfigured,
  initialModel,
}) {
  const [status, setStatus] = useState(initialStatus ?? 'not_configured');
  const [configured, setConfigured] = useState(initialConfigured ?? false);
  const [model, setModel] = useState(initialModel ?? null);
  const [loading, setLoading] = useState(!initialStatus);
  const [error, setError] = useState('');

  const load = () => {
    setLoading(true);
    setError('');
    return fetchGroqProviderStatus()
      .then(data => {
        setStatus(data.status ?? 'not_configured');
        setConfigured(data.configured === true);
        setModel(data.model ?? null);
      })
      .catch(err => setError(err.message || 'Could not load Groq feedback status.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (initialStatus) setStatus(initialStatus);
    if (initialConfigured !== undefined) setConfigured(initialConfigured);
    if (initialModel !== undefined) setModel(initialModel);
  }, [initialStatus, initialConfigured, initialModel]);

  return (
    <Card style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h2 style={{ fontSize: 16, margin: '0 0 6px' }}>Groq Participant Feedback</h2>
          <p style={{ fontSize: 13, color: T.muted, margin: 0, maxWidth: 520, lineHeight: 1.6 }}>
            Per-participant research estimates are generated with Groq when you release feedback for selected participants.
          </p>
        </div>
        <div style={{ textAlign: 'right' }}>
          {loading ? (
            <p style={{ fontSize: 13, color: T.muted, margin: 0 }}>Checking provider…</p>
          ) : (
            <>
              <div style={{ fontSize: 13, marginBottom: 6 }}>
                Groq Feedback:{' '}
                <strong style={{ color: statusColor(status) }}>{statusLabel(status)}</strong>
              </div>
              {model && (
                <p style={{ fontSize: 12, color: T.muted, margin: '0 0 8px' }}>
                  Model: {model}
                </p>
              )}
              {!configured && status === 'not_configured' && (
                <p style={{ fontSize: 12, color: T.orange, margin: '0 0 8px' }}>
                  Set GROQ_API_KEY and GROQ_MODEL on the server to enable feedback generation.
                </p>
              )}
            </>
          )}
          <Btn onClick={load} disabled={loading} style={{ fontSize: 12 }}>
            Refresh Status
          </Btn>
        </div>
      </div>
      {error && <p role="alert" style={{ color: T.red, fontSize: 13, marginTop: 12, marginBottom: 0 }}>{error}</p>}
    </Card>
  );
}
