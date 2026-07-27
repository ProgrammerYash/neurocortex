import { useState } from 'react';
import {
  goldenVaultAddCoins,
  goldenVaultAddSessions,
  goldenVaultDeleteCoins,
  goldenVaultDeleteSessions,
} from '../../store/goldenVault.js';

function parseAmount(raw) {
  const trimmed = String(raw ?? '').trim();
  if (!/^\d+$/.test(trimmed)) return null;
  const value = Number.parseInt(trimmed, 10);
  return value >= 1 ? value : null;
}

export function SessionCoinControls({ row, disabled, onUpdated }) {
  const [sessionAmount, setSessionAmount] = useState('1');
  const [coinAmount, setCoinAmount] = useState('1');
  const [error, setError] = useState('');

  const run = async (fn) => {
    setError('');
    try {
      await fn();
      onUpdated?.();
    } catch (err) {
      setError(err?.message || 'Action failed');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 200 }}>
      <div style={{ display: 'flex', gap: 4, alignItems: 'center', flexWrap: 'wrap' }}>
        <label style={{ fontSize: 10 }}>Sessions</label>
        <input
          type="number"
          min="1"
          step="1"
          value={sessionAmount}
          onChange={e => setSessionAmount(e.target.value)}
          data-testid={`session-amount-${row.participantId}`}
          style={{ width: 56, padding: 4 }}
        />
        <button type="button" className="golden-vault-btn" disabled={disabled} onClick={() => {
          const amount = parseAmount(sessionAmount);
          if (!amount) { setError('Enter a whole number ≥ 1 for sessions.'); return; }
          run(() => goldenVaultAddSessions(row.participantId, amount));
        }}>Add</button>
        <button type="button" className="golden-vault-btn" disabled={disabled} onClick={() => {
          const amount = parseAmount(sessionAmount);
          if (!amount) { setError('Enter a whole number ≥ 1 for sessions.'); return; }
          run(() => goldenVaultDeleteSessions(row.participantId, amount));
        }}>Delete</button>
      </div>
      <div style={{ display: 'flex', gap: 4, alignItems: 'center', flexWrap: 'wrap' }}>
        <label style={{ fontSize: 10 }}>Coins</label>
        <input
          type="number"
          min="1"
          step="1"
          value={coinAmount}
          onChange={e => setCoinAmount(e.target.value)}
          data-testid={`coin-amount-${row.participantId}`}
          style={{ width: 56, padding: 4 }}
        />
        <button type="button" className="golden-vault-btn" disabled={disabled} onClick={() => {
          const amount = parseAmount(coinAmount);
          if (!amount) { setError('Enter a whole number ≥ 1 for coins.'); return; }
          run(() => goldenVaultAddCoins(row.participantId, amount));
        }}>Add</button>
        <button type="button" className="golden-vault-btn" disabled={disabled} onClick={() => {
          const amount = parseAmount(coinAmount);
          if (!amount) { setError('Enter a whole number ≥ 1 for coins.'); return; }
          run(() => goldenVaultDeleteCoins(row.participantId, amount));
        }}>Delete</button>
      </div>
      {error && <span style={{ fontSize: 10, color: '#f87171' }}>{error}</span>}
      <span style={{ fontSize: 10, color: '#9a9285' }}>Displayed sessions: {row.displayedCompletedSessions}</span>
    </div>
  );
}
