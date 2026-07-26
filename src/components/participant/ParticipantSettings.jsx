import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Btn from '../ui/Btn.jsx';
import ButtonSpinner from '../ui/ButtonSpinner.jsx';
import Card from '../ui/Card.jsx';
import Page from '../ui/Page.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';
import StudyFrequencySelector from './StudyFrequencySelector.jsx';
import { useParticipantTheme } from './ParticipantAppShell.jsx';
import { PARTICIPANT_THEME_OPTIONS } from '../../store/participantTheme.js';
import { studyFrequencyLabel } from '../../constants/studyFrequency.js';
import { updateParticipantStudyFrequency } from '../../store/preferences.js';
import { ROUTES } from '../../routing/routePaths.js';

const THEME_LABELS = { system: 'System', light: 'Light', dark: 'Dark' };

export default function ParticipantSettings({ user, onStudyFrequencySaved, showToast }) {
  const navigate = useNavigate();
  const { theme, setTheme } = useParticipantTheme();
  const initialFrequency = user?.studyFrequency ?? '';
  const [draftTheme, setDraftTheme] = useState(theme);
  const [schedule, setSchedule] = useState(initialFrequency);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  const saveLock = useRef(false);

  useEffect(() => {
    setDraftTheme(theme);
  }, [theme]);

  useEffect(() => {
    setSchedule(initialFrequency);
  }, [initialFrequency]);

  const dirty = useMemo(
    () => draftTheme !== theme || (schedule !== initialFrequency && Boolean(schedule)),
    [draftTheme, theme, schedule, initialFrequency],
  );

  const currentLabel = useMemo(
    () => studyFrequencyLabel(user?.studyFrequency),
    [user?.studyFrequency],
  );

  const saveSettings = async () => {
    if (!dirty || saving || saveLock.current) return;
    saveLock.current = true;
    setSaving(true);
    setSaveError('');
    try {
      if (draftTheme !== theme) {
        setTheme(draftTheme);
      }
      if (schedule !== initialFrequency && schedule) {
        const response = await updateParticipantStudyFrequency(schedule);
        await onStudyFrequencySaved?.(response.study_frequency);
      }
      showToast?.('Settings saved.', 'success');
    } catch (err) {
      setSaveError(err?.message || 'Could not save your settings.');
    } finally {
      setSaving(false);
      saveLock.current = false;
    }
  };

  return (
    <Page title="Participant Settings" onBack={() => navigate(ROUTES.participantDashboard)}>
      <div style={{ maxWidth: 720, margin: '0 auto', display: 'grid', gap: 16 }}>
        <Card className="participant-card fade-in">
          <SectionTitle>Appearance</SectionTitle>
          <p className="participant-muted" style={{ fontSize: 13, marginBottom: 14 }}>
            Choose how NeuroCortex looks on your participant screens. System follows your device light or dark mode.
          </p>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {PARTICIPANT_THEME_OPTIONS.map(option => (
              <Btn
                key={option}
                primary={draftTheme === option}
                onClick={() => setDraftTheme(option)}
                aria-pressed={draftTheme === option}
                disabled={saving}
                style={{ minWidth: 120 }}
              >
                {THEME_LABELS[option]}
              </Btn>
            ))}
          </div>
        </Card>

        <Card className="participant-card fade-in">
          <SectionTitle>Study Schedule</SectionTitle>
          <p className="participant-muted" style={{ fontSize: 13, marginBottom: 8 }}>
            Current schedule: <strong>{currentLabel}</strong>
          </p>
          <StudyFrequencySelector value={schedule} onChange={setSchedule} disabled={saving} />
        </Card>

        {saveError ? (
          <p role="alert" style={{ color: '#fc8181', fontSize: 13, margin: 0 }}>{saveError}</p>
        ) : null}

        <Btn
          primary
          style={{ width: '100%', padding: 12 }}
          disabled={!dirty || saving}
          onClick={saveSettings}
          data-testid="participant-settings-save"
        >
          {saving ? (
            <>
              <ButtonSpinner size={14} />
              Saving…
            </>
          ) : (
            'Save'
          )}
        </Btn>

        <Btn onClick={() => navigate(ROUTES.participantDashboard)} style={{ justifySelf: 'start' }}>
          ← Back to Dashboard
        </Btn>
      </div>
    </Page>
  );
}
