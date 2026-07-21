import { useState } from 'react';
import { T } from '../../constants/tokens.js';
import { changePinWithApi } from '../../store/auth.js';
import { ApiError } from '../../store/apiClient.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';
import Label from '../ui/Label.jsx';

export default function ChangePinScreen({ onComplete, onLogout }) {
  const [pin, setPin] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setError('');
    if (!/^\d{4,6}$/.test(pin)) {
      setError('Enter a 4–6 digit PIN.');
      return;
    }
    if (pin !== confirm) {
      setError('PIN confirmation does not match.');
      return;
    }
    setLoading(true);
    try {
      await changePinWithApi({ pin, pinConfirmation: confirm });
      setPin('');
      setConfirm('');
      await onComplete();
    } catch (err) {
      const message = err instanceof ApiError ? err.message : err?.message || 'Could not update PIN.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Page title="Create a New PIN" onBack={onLogout}>
      <Card style={{ maxWidth: 420, margin: '0 auto' }} className="fade-in">
        <SectionTitle>Create a New PIN</SectionTitle>
        <p style={{ fontSize: 13, color: T.muted, marginBottom: 16 }}>
          Your PIN was reset. Choose a new PIN before continuing.
        </p>
        <Label>New PIN</Label>
        <input
          type="password"
          inputMode="numeric"
          maxLength={6}
          value={pin}
          onChange={e => { setPin(e.target.value.replace(/\D/g, '')); setError(''); }}
          style={{ fontFamily: T.mono, fontSize: 15, marginBottom: 12, letterSpacing: 4 }}
        />
        <Label>Confirm new PIN</Label>
        <input
          type="password"
          inputMode="numeric"
          maxLength={6}
          value={confirm}
          onChange={e => { setConfirm(e.target.value.replace(/\D/g, '')); setError(''); }}
          onKeyDown={e => e.key === 'Enter' && submit()}
          style={{ fontFamily: T.mono, fontSize: 15, marginBottom: 12, letterSpacing: 4 }}
        />
        <p style={{ fontSize: 12, color: T.muted, marginBottom: 12 }}>Use 4–6 digits only.</p>
        {error && (
          <div style={{ background: 'rgba(252,129,129,0.12)', border: '1px solid rgba(252,129,129,0.35)', borderRadius: 8, padding: '9px 13px', color: T.red, fontSize: 13, marginBottom: 10 }}>
            {error}
          </div>
        )}
        <Btn onClick={submit} primary style={{ width: '100%', padding: '13px' }} disabled={loading}>
          {loading ? 'Saving…' : 'Save new PIN'}
        </Btn>
      </Card>
    </Page>
  );
}
