import { useEffect, useState } from 'react';
import { T } from '../../constants/tokens.js';
import { fetchStudySettings, updateStudySettings } from '../../store/research.js';
import Btn from '../ui/Btn.jsx';
import Card from '../ui/Card.jsx';

export default function StudyFeedbackControl({ showToast }) {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const load = () => {
    setLoading(true);
    setError('');
    return fetchStudySettings()
      .then(data => setSettings(data))
      .catch(err => setError(err.message || 'Could not load study settings.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const releaseEnabled = settings?.participant_feedback_enabled === true;
  const modelReady = settings?.model_configured === true;

  const applyToggle = async nextValue => {
    if (saving) return;
    if (nextValue && !modelReady) return;
    if (nextValue) {
      const ok = window.confirm(
        'Release Participant Feedback?\n\nParticipants will be able to view non-diagnostic research estimates generated from their current study data.',
      );
      if (!ok) return;
    } else {
      const ok = window.confirm('Turn off participant research feedback?');
      if (!ok) return;
    }
    setSaving(true);
    try {
      const updated = await updateStudySettings({ participant_feedback_enabled: nextValue });
      setSettings(updated);
      showToast?.(
        nextValue ? 'Participant feedback released.' : 'Participant feedback turned off.',
        'success',
      );
    } catch (err) {
      showToast?.(err.message || 'Could not update study settings.', 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading && !settings) {
    return (
      <Card style={{ marginBottom: 16 }}>
        <p style={{ color: T.muted, fontSize: 13, margin: 0 }}>Loading study settings…</p>
      </Card>
    );
  }

  return (
    <Card style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h2 style={{ fontSize: 16, margin: '0 0 6px' }}>Release Participant Feedback</h2>
          <p style={{ fontSize: 13, color: T.muted, margin: 0, maxWidth: 520, lineHeight: 1.6 }}>
            Allow participants to view research estimates generated from their current study data.
          </p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 13, marginBottom: 8 }}>
            Participant Feedback:{' '}
            <strong>{releaseEnabled ? 'Released' : 'Off'}</strong>
          </div>
          {!modelReady && (
            <p style={{ fontSize: 12, color: T.orange, margin: '0 0 8px' }}>Model Not Configured</p>
          )}
          <Btn
            disabled={saving || (!releaseEnabled && !modelReady)}
            onClick={() => applyToggle(!releaseEnabled)}
            primary={!releaseEnabled}
          >
            {saving ? 'Saving…' : releaseEnabled ? 'Turn Off Feedback' : 'Release Feedback'}
          </Btn>
        </div>
      </div>
      {error && <p role="alert" style={{ color: T.red, fontSize: 13, marginTop: 12 }}>{error}</p>}
      {settings?.model_version && (
        <p style={{ fontSize: 11, color: T.muted, marginTop: 12, marginBottom: 0 }}>
          Configured model version: {settings.model_version}
        </p>
      )}
    </Card>
  );
}
