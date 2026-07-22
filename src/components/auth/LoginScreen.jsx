import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { T } from '../../constants/tokens.js';
import Store from '../../store/index.js';
import { ApiError } from '../../store/apiClient.js';
import { fetchRecentParticipantStatus } from '../../store/auth.js';
import {
  getRecentParticipants,
  migrateRecentFromLegacyIndex,
  pruneRecentParticipants,
  removeRecentParticipant,
  RECENT_PARTICIPANTS_EVENT,
} from '../../store/recentParticipants.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';
import Label from '../ui/Label.jsx';
import { ROUTES } from '../../routing/routePaths.js';

const RECENT_LOGIN_REMOVAL_CODES = new Set(['ACCOUNT_REMOVED', 'ACCOUNT_DISABLED']);

export default function LoginScreen({ onLogin, onBack }) {
  const [id, setId] = useState('');
  const [pin, setPin] = useState('');
  const [loginError, setLoginError] = useState('');
  const [loading, setLoading] = useState(false);
  const [recentParticipants, setRecentParticipants] = useState(() => getRecentParticipants());
  const navigate = useNavigate();

  const refreshRecentList = useCallback(() => {
    setRecentParticipants(getRecentParticipants());
  }, []);

  useEffect(() => {
    migrateRecentFromLegacyIndex(
      Store.getLocalParticipants?.()?.map(p => p.id) ?? [],
      pid => Store.getParticipant(pid),
    );
    refreshRecentList();
  }, [refreshRecentList]);

  useEffect(() => {
    const onStorage = event => {
      if (event.key === 'nc3_recent_participants') refreshRecentList();
    };
    window.addEventListener(RECENT_PARTICIPANTS_EVENT, refreshRecentList);
    window.addEventListener('storage', onStorage);
    return () => {
      window.removeEventListener(RECENT_PARTICIPANTS_EVENT, refreshRecentList);
      window.removeEventListener('storage', onStorage);
    };
  }, [refreshRecentList]);

  useEffect(() => {
    let cancelled = false;
    const ids = getRecentParticipants().map(p => p.id);
    if (!ids.length || import.meta.env.VITE_USE_LOCAL_STORE === 'true') return undefined;

    (async () => {
      try {
        const statuses = await fetchRecentParticipantStatus(ids);
        if (cancelled) return;
        const eligible = statuses
          .filter(row => row.recent_eligible)
          .map(row => row.public_id);
        pruneRecentParticipants(eligible);
        refreshRecentList();
      } catch {
        // retain list on network failure
      }
    })();

    return () => { cancelled = true; };
  }, [refreshRecentList]);

  const submit = async () => {
    setLoginError('');
    const pid = id.trim().toUpperCase();
    if (!pid) { setLoginError('Please enter your Participant ID.'); return; }
    if (!/^\d{4,6}$/.test(pin)) {
      setLoginError('Please enter your 4–6 digit PIN.');
      return;
    }

    setLoading(true);
    try {
      const profile = await Store.loginParticipant({ publicId: pid, pin });
      await onLogin(profile);
    } catch (error) {
      const message = error instanceof ApiError
        ? error.message
        : error?.message || 'Sign in failed. Please try again.';
      setLoginError(message);
      if (error instanceof ApiError && RECENT_LOGIN_REMOVAL_CODES.has(error.errorCode)) {
        removeRecentParticipant(pid);
        refreshRecentList();
      }
    } finally {
      setLoading(false);
    }
  };

  const visibleRecent = recentParticipants.slice(-6).reverse();

  return (
    <Page title="Sign In" onBack={onBack ?? (() => navigate(ROUTES.home))}>
      <Card style={{ maxWidth: 420, margin: '0 auto' }} className="fade-in">
        <SectionTitle>Enter your Participant ID</SectionTitle>
        <input
          value={id}
          onChange={e => { setId(e.target.value.toUpperCase()); setLoginError(''); }}
          placeholder="NC-XXXXXXXXXXXXXXXX"
          style={{ fontFamily: T.mono, fontSize: 15, marginBottom: 14, letterSpacing: 2 }}
        />
        <Label>PIN</Label>
        <input
          type="password"
          inputMode="numeric"
          maxLength={6}
          value={pin}
          onChange={e => { setPin(e.target.value.replace(/\D/g, '')); setLoginError(''); }}
          onKeyDown={e => e.key === 'Enter' && submit()}
          placeholder="4–6 digit PIN"
          style={{ fontFamily: T.mono, fontSize: 15, marginBottom: 6, letterSpacing: 4 }}
        />
        {loginError && (
          <div style={{ background: 'rgba(252,129,129,0.12)', border: '1px solid rgba(252,129,129,0.35)', borderRadius: 8, padding: '9px 13px', color: T.red, fontSize: 13, marginBottom: 10 }}>
            {loginError}
          </div>
        )}
        <Btn onClick={submit} primary style={{ width: '100%', padding: '13px', marginTop: 4 }} disabled={loading}>
          {loading ? 'Signing in…' : 'Sign In →'}
        </Btn>
        {visibleRecent.length > 0 && (
          <>
            <div style={{ fontSize: 12, color: T.muted, margin: '20px 0 10px', textAlign: 'center' }}>Recent participants on this device:</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {visibleRecent.map(p => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => { setId(p.id); setLoginError(''); }}
                  style={{ background: T.surface, border: `1px solid ${T.faint}`, borderRadius: 8, padding: '10px 14px', color: T.text, fontSize: 13, textAlign: 'left', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                >
                  <span style={{ fontFamily: T.mono, fontSize: 12, color: T.teal }}>{p.id}</span>
                  <span style={{ color: T.muted, fontSize: 11 }}>{p.grade ?? '—'}{p.ageRange ? ` · ${p.ageRange}` : ''}</span>
                </button>
              ))}
            </div>
          </>
        )}
      </Card>
    </Page>
  );
}
