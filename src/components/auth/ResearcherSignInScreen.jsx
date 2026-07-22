import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { T } from '../../constants/tokens.js';
import Store from '../../store/index.js';
import { ApiError } from '../../store/apiClient.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';
import Label from '../ui/Label.jsx';
import { ROUTES } from '../../routing/routePaths.js';

export default function ResearcherSignInScreen({ onLogin, onBack }) {
  const [resCode, setResCode] = useState('');
  const [formError, setFormError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const submitResearcher = async event => {
    event?.preventDefault?.();
    if (loading) return;
    setFormError('');
    if (!resCode.trim()) return setFormError('Please enter your access code.');
    setLoading(true);
    try {
      await onLogin(await Store.loginResearcher({ inviteCode: resCode }));
      navigate(ROUTES.researcherDashboard, { replace: true });
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : error?.message || 'Researcher sign-in failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Page title="Researcher Sign In" onBack={onBack ?? (() => navigate(ROUTES.home))}>
      <Card style={{ maxWidth: 460, margin: '0 auto' }} className="fade-in">
        <SectionTitle>Researcher sign-in</SectionTitle>
        <form onSubmit={submitResearcher}>
          <Label>Researcher Access Code</Label>
          <input
            type="password"
            value={resCode}
            onChange={e => { setResCode(e.target.value); setFormError(''); }}
            placeholder="Enter access code (case-insensitive)"
            disabled={loading}
            autoComplete="current-password"
          />
          <p style={{ fontSize: 11, color: T.muted, marginTop: 6, lineHeight: 1.6 }}>
            Code is case-insensitive. Contact the study coordinator.
          </p>
          {formError && (
            <div role="alert" style={{ background: 'rgba(252,129,129,.12)', border: '1px solid rgba(252,129,129,.35)', borderRadius: 8, padding: '9px 13px', color: T.red, fontSize: 13, marginTop: 10 }}>
              {formError}
            </div>
          )}
          <Btn type="submit" primary style={{ width: '100%', marginTop: 20, padding: 13 }} disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In as Researcher →'}
          </Btn>
        </form>
      </Card>
    </Page>
  );
}
