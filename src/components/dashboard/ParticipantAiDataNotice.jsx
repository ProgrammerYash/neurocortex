import { T } from '../../constants/tokens.js';
import {
  PARTICIPANT_AI_TRAINING_DETAIL,
  PARTICIPANT_AI_TRAINING_SUMMARY,
} from '../../constants/participantAiMessaging.js';
import Card from '../ui/Card.jsx';

export default function ParticipantAiDataNotice() {
  return (
    <Card style={{ marginBottom: 16 }} aria-labelledby="participant-ai-notice-heading">
      <h2 id="participant-ai-notice-heading" style={{ fontSize: 15, margin: '0 0 8px' }}>
        Your data and the AI model
      </h2>
      <p style={{ fontSize: 13, margin: '0 0 6px', lineHeight: 1.6 }}>{PARTICIPANT_AI_TRAINING_SUMMARY}</p>
      <p style={{ fontSize: 12, color: T.muted, margin: 0, lineHeight: 1.6 }}>{PARTICIPANT_AI_TRAINING_DETAIL}</p>
    </Card>
  );
}
