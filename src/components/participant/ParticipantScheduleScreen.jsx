import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Btn from '../ui/Btn.jsx';
import Card from '../ui/Card.jsx';
import Page from '../ui/Page.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';
import StudyFrequencySelector from './StudyFrequencySelector.jsx';
import { updateParticipantStudyFrequency } from '../../store/preferences.js';
import { ROUTES } from '../../routing/routePaths.js';

export default function ParticipantScheduleScreen({ onSaved, onBack }) {
  const [value, setValue] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const saveLock = useRef(false);
  const navigate = useNavigate();

  const save = async () => {
    if (!value || saving || saveLock.current) return;
    saveLock.current = true;
    setSaving(true);
    setError('');
    try {
      const response = await updateParticipantStudyFrequency(value);
      await onSaved?.(response.study_frequency);
      navigate(ROUTES.participantDashboard, { replace: true });
    } catch (err) {
      setError(err?.message || 'Could not save your study schedule. Please try again.');
    } finally {
      setSaving(false);
      saveLock.current = false;
    }
  };

  return (
    <Page
      title="Choose Your Study Schedule"
      onBack={onBack ?? (() => navigate(ROUTES.home))}
    >
      <Card className="participant-card fade-in" style={{ maxWidth: 720, margin: '0 auto' }}>
        <SectionTitle>Choose Your Study Schedule</SectionTitle>
        <p className="participant-muted" style={{ fontSize: 14, lineHeight: 1.7, marginBottom: 18 }}>
          Select how often you plan to complete a NeuroCortex session. You can change this later in Settings.
        </p>
        <StudyFrequencySelector value={value} onChange={setValue} disabled={saving} />
        {error ? <p role="alert" style={{ color: '#fc8181', marginTop: 14, fontSize: 13 }}>{error}</p> : null}
        <Btn
          primary
          style={{ width: '100%', marginTop: 20, padding: 13 }}
          disabled={!value || saving}
          onClick={save}
        >
          {saving ? 'Saving…' : 'Save and Continue'}
        </Btn>
      </Card>
    </Page>
  );
}
