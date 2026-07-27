import { useEffect, useState } from 'react';
import {
  PARTICIPANT_AI_FEEDBACK_TRAINING_NOTE,
  PARTICIPANT_AI_TRAINING_DETAIL,
} from '../../constants/participantAiMessaging.js';
import { fetchParticipantModelFeedback } from '../../store/participantFeedback.js';
import Card from '../ui/Card.jsx';
import { useParticipantTokens } from '../participant/ParticipantAppShell.jsx';

export default function ResearchFeedbackCard() {
  const P = useParticipantTokens();
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

  if (error) {
    return (
      <Card style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 16, margin: '0 0 8px' }}>Research Feedback</h2>
        <p role="alert" style={{ color: P.muted, fontSize: 13, margin: 0 }}>{error}</p>
      </Card>
    );
  }

  if (!feedback?.status || feedback.status === 'disabled') return null;

  const warningText = feedback.warning;

  return (
    <Card style={{ marginBottom: 16 }} data-testid="research-feedback-card">
      <h2 style={{ fontSize: 16, margin: '0 0 10px' }}>Research Feedback</h2>

      {feedback.status === 'not_released' && (
        <p style={{ fontSize: 13, color: P.muted, margin: 0, lineHeight: 1.6 }}>
          Personalized research feedback has not been released for your account yet. Your study team will share an estimate when it is ready.
        </p>
      )}

      {feedback.status === 'insufficient_data' && (
        <>
          {feedback.headline ? (
            <p style={{ fontWeight: 600, margin: '0 0 6px' }}>{feedback.headline}</p>
          ) : (
            <p style={{ fontWeight: 600, margin: '0 0 6px' }}>{feedback.label || 'Not enough data yet'}</p>
          )}
          <p style={{ fontSize: 13, color: P.muted, margin: '0 0 8px', lineHeight: 1.6 }}>
            {feedback.summary || `Complete more study sessions before a research estimate can be generated. ${PARTICIPANT_AI_TRAINING_DETAIL}`}
          </p>
          {warningText ? (
            <p style={{ fontSize: 12, color: P.muted, margin: 0, lineHeight: 1.6 }}>{warningText}</p>
          ) : null}
        </>
      )}

      {feedback.status === 'available' && (
        <>
          {feedback.level ? (
            <p style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.06em', color: P.teal, margin: '0 0 6px' }}>
              {feedback.level.replace(/_/g, ' ')}
            </p>
          ) : null}
          {feedback.headline ? (
            <p style={{ fontWeight: 600, margin: '0 0 6px' }}>{feedback.headline}</p>
          ) : feedback.label ? (
            <p style={{ fontWeight: 600, margin: '0 0 6px' }}>{feedback.label}</p>
          ) : null}
          {feedback.summary ? (
            <p style={{ fontSize: 13, color: P.muted, margin: '0 0 8px', lineHeight: 1.6 }}>{feedback.summary}</p>
          ) : null}
          {Array.isArray(feedback.factors) && feedback.factors.length > 0 ? (
            <ul style={{ fontSize: 13, color: P.muted, margin: '0 0 8px', paddingLeft: 18, lineHeight: 1.6 }}>
              {feedback.factors.map(factor => (
                <li key={factor}>{factor}</li>
              ))}
            </ul>
          ) : null}
          {feedback.generated_at && (
            <p style={{ fontSize: 12, color: P.muted, margin: '0 0 8px' }}>
              Updated {new Date(feedback.generated_at).toLocaleString()}
            </p>
          )}
          <p style={{ fontSize: 12, color: P.muted, margin: '0 0 8px', lineHeight: 1.6 }}>
            {PARTICIPANT_AI_FEEDBACK_TRAINING_NOTE}
          </p>
          {warningText ? (
            <p style={{ fontSize: 12, color: P.muted, margin: 0, lineHeight: 1.6 }}>{warningText}</p>
          ) : null}
        </>
      )}
    </Card>
  );
}
