import { useEffect, useState } from 'react';
import { T } from '../../constants/tokens.js';
import {
  PARTICIPANT_AI_FEEDBACK_TRAINING_NOTE,
  PARTICIPANT_AI_TRAINING_DETAIL,
} from '../../constants/participantAiMessaging.js';
import { fetchParticipantModelFeedback } from '../../store/participantFeedback.js';
import Card from '../ui/Card.jsx';

const DISCLAIMER =
  'This is a research estimate, not a medical or psychological diagnosis.';

export default function ResearchFeedbackCard() {
  const [feedback, setFeedback] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    fetchParticipantModelFeedback()
      .then(data => {
        if (!active) return;
        setFeedback(data);
      })
      .catch(err => {
        if (!active) return;
        setError(err.message || 'Research feedback is unavailable.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  if (loading) return null;
  if (feedback?.status === 'disabled') return null;
  if (error) {
    return (
      <Card style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 16, margin: '0 0 8px' }}>Research Feedback</h2>
        <p role="alert" style={{ color: T.muted, fontSize: 13, margin: 0 }}>{error}</p>
      </Card>
    );
  }

  return (
    <Card style={{ marginBottom: 16 }}>
      <h2 style={{ fontSize: 16, margin: '0 0 10px' }}>Research Feedback</h2>
      {feedback?.status === 'insufficient_data' && (
        <>
          <p style={{ fontWeight: 600, margin: '0 0 6px' }}>{feedback.label || 'Not enough data yet'}</p>
          <p style={{ fontSize: 13, color: T.muted, margin: '0 0 8px', lineHeight: 1.6 }}>
            Complete more study sessions before a research estimate can be generated. {PARTICIPANT_AI_TRAINING_DETAIL}
          </p>
        </>
      )}
      {feedback?.status === 'available' && (
        <>
          <p style={{ fontWeight: 600, margin: '0 0 6px' }}>{feedback.label}</p>
          {feedback.generated_at && (
            <p style={{ fontSize: 12, color: T.muted, margin: '0 0 8px' }}>
              Updated {new Date(feedback.generated_at).toLocaleString()}
            </p>
          )}
          <p style={{ fontSize: 12, color: T.muted, margin: '0 0 8px', lineHeight: 1.6 }}>
            {PARTICIPANT_AI_FEEDBACK_TRAINING_NOTE}
          </p>
          <p style={{ fontSize: 12, color: T.muted, margin: 0, lineHeight: 1.6 }}>{DISCLAIMER}</p>
        </>
      )}
    </Card>
  );
}
