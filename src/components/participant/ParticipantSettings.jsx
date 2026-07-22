import { useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Btn from '../ui/Btn.jsx';
import Card from '../ui/Card.jsx';
import Page from '../ui/Page.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';
import StudyFrequencySelector from './StudyFrequencySelector.jsx';
import { useParticipantTheme } from './ParticipantAppShell.jsx';
import { studyFrequencyLabel } from '../../constants/studyFrequency.js';
import { updateParticipantStudyFrequency } from '../../store/preferences.js';
import { ROUTES } from '../../routing/routePaths.js';

export default function ParticipantSettings({ user, onStudyFrequencySaved, showToast }) {
  const navigate = useNavigate();
  const { theme, setTheme } = useParticipantTheme();
  const initialFrequency = user?.studyFrequency ?? '';
  const [schedule, setSchedule] = useState(initialFrequency);
  const [savingSchedule, setSavingSchedule] = useState(false);
  const [scheduleError, setScheduleError] = useState('');
  const saveLock = useRef(false);

  const scheduleDirty = schedule !== initialFrequency && Boolean(schedule);

  const currentLabel = useMemo(
    () => studyFrequencyLabel(user?.studyFrequency),
    [user?.studyFrequency],
  );

  const saveSchedule = async () => {
    if (!scheduleDirty || savingSchedule || saveLock.current) return;
    saveLock.current = true;
    setSavingSchedule(true);
    setScheduleError('');
    try {
      const response = await updateParticipantStudyFrequency(schedule);
      await onStudyFrequencySaved?.(response.study_frequency);
      showToast?.('Study schedule updated.', 'success');
    } catch (err) {
      setScheduleError(err?.message || 'Could not save your study schedule.');
    } finally {
      setSavingSchedule(false);
      saveLock.current = false;
    }
  };

  return (
    <Page title="Participant Settings" onBack={() => navigate(ROUTES.participantDashboard)}>
      <div style={{ maxWidth: 720, margin: '0 auto', display: 'grid', gap: 16 }}>
        <Card className="participant-card fade-in">
          <SectionTitle>Appearance</SectionTitle>
          <p className="participant-muted" style={{ fontSize: 13, marginBottom: 14 }}>
            Choose how NeuroCortex looks on your participant screens.
          </p>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {['dark', 'light'].map(option => (
              <Btn
                key={option}
                primary={theme === option}
                onClick={() => setTheme(option)}
                aria-pressed={theme === option}
                style={{ minWidth: 120, textTransform: 'capitalize' }}
              >
                {option}
              </Btn>
            ))}
          </div>
        </Card>

        <Card className="participant-card fade-in">
          <SectionTitle>Study Schedule</SectionTitle>
          <p className="participant-muted" style={{ fontSize: 13, marginBottom: 8 }}>
            Current schedule: <strong>{currentLabel}</strong>
          </p>
          <StudyFrequencySelector value={schedule} onChange={setSchedule} disabled={savingSchedule} />
          {scheduleError ? <p role="alert" style={{ color: '#fc8181', marginTop: 12, fontSize: 13 }}>{scheduleError}</p> : null}
          <Btn
            primary
            style={{ width: '100%', marginTop: 16, padding: 12 }}
            disabled={!scheduleDirty || savingSchedule}
            onClick={saveSchedule}
          >
            {savingSchedule ? 'Saving…' : 'Save Schedule'}
          </Btn>
        </Card>

        <Btn onClick={() => navigate(ROUTES.participantDashboard)} style={{ justifySelf: 'start' }}>
          ← Back to Dashboard
        </Btn>
      </div>
    </Page>
  );
}
