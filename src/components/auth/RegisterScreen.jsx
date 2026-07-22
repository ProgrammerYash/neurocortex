import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Store from '../../store/index.js';
import { ApiError } from '../../store/apiClient.js';
import Page from '../ui/Page.jsx';
import ConsentWizard from '../consent/ConsentWizard.jsx';
import { ROUTES } from '../../routing/routePaths.js';

export default function RegisterScreen({ onRegister, onBack, showToast }) {
  const [formError, setFormError] = useState('');
  const [loading, setLoading] = useState(false);
  const submitLock = useRef(false);
  const navigate = useNavigate();

  const submitParticipant = async body => {
    if (submitLock.current) return;
    submitLock.current = true;
    setLoading(true);
    setFormError('');
    try {
      const profile = await Store.registerParticipant(body);
      showToast?.(`Your assent and parent/guardian permission were recorded. Your Participant ID is ${profile.id}. Save this ID for sign-in.`, 'success');
      await onRegister(profile);
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : error?.message || 'Registration failed. Please try again.');
      throw error;
    } finally {
      submitLock.current = false;
      setLoading(false);
    }
  };

  return (
    <Page title="Join the Study" onBack={onBack ?? (() => navigate(ROUTES.home))}>
      <ConsentWizard registration onSubmit={submitParticipant} submitting={loading} error={formError} />
    </Page>
  );
}
