import { useEffect, useState } from 'react';
import { T } from '../../constants/tokens.js';
import Btn from '../ui/Btn.jsx';
import { fetchSentParticipantMessages, sendParticipantMessage } from '../../store/messages.js';

const MAX_SUBJECT = 150;
const MAX_BODY = 5000;

export default function ParticipantMessaging({ detail, showToast }) {
  const [showComposer, setShowComposer] = useState(false);
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [messages, setMessages] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [historyError, setHistoryError] = useState('');
  const [expandedId, setExpandedId] = useState('');

  const loadHistory = () => {
    if (!detail?.participantId) return Promise.resolve();
    setLoadingHistory(true);
    setHistoryError('');
    return fetchSentParticipantMessages(detail.participantId)
      .then(data => setMessages(Array.isArray(data.items) ? data.items : []))
      .catch(err => {
        setMessages([]);
        setHistoryError(err.message || 'Could not load sent messages.');
      })
      .finally(() => setLoadingHistory(false));
  };

  useEffect(() => {
    setShowComposer(false);
    setSubject('');
    setBody('');
    setError('');
    setExpandedId('');
    loadHistory();
  }, [detail?.participantId]);

  const sendMessage = async () => {
    const cleanedSubject = subject.trim();
    const cleanedBody = body.trim();
    if (!cleanedSubject || !cleanedBody) {
      setError('Subject and message are required.');
      return;
    }
    if (cleanedSubject.length > MAX_SUBJECT || cleanedBody.length > MAX_BODY) {
      setError('Message exceeds allowed length.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      await sendParticipantMessage(detail.participantId, {
        subject: cleanedSubject,
        body: cleanedBody,
      });
      setShowComposer(false);
      setSubject('');
      setBody('');
      showToast?.('Message sent.', 'success');
      await loadHistory();
    } catch (err) {
      setError(err.message || 'Could not send message.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section style={{ marginTop: 18, borderTop: `1px solid ${T.faint}`, paddingTop: 18 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', marginBottom: 10 }}>
        <h3 style={{ fontSize: 12, color: T.muted, textTransform: 'uppercase', letterSpacing: 1, margin: 0 }}>
          Send message
        </h3>
        {!showComposer && (
          <Btn onClick={() => setShowComposer(true)} disabled={detail?.isRemoved}>
            Send Message
          </Btn>
        )}
      </div>

      {showComposer && (
        <div style={{ background: T.surface, borderRadius: 10, padding: 14, border: `1px solid ${T.faint}`, marginBottom: 14 }}>
          <div style={{ fontSize: 13, marginBottom: 10 }}>
            To: <strong>{detail.participantId}</strong>
            {detail.studentName ? <> · <strong>{detail.studentName}</strong></> : null}
          </div>
          <label style={{ display: 'block', marginBottom: 10 }}>
            <div style={{ fontSize: 11, color: T.muted, marginBottom: 4 }}>Subject</div>
            <input
              value={subject}
              maxLength={MAX_SUBJECT}
              aria-label="Subject"
              onChange={event => setSubject(event.target.value)}
              style={{ width: '100%' }}
            />
            <div style={{ fontSize: 11, color: T.muted, marginTop: 4 }}>{subject.trim().length}/{MAX_SUBJECT}</div>
          </label>
          <label style={{ display: 'block', marginBottom: 10 }}>
            <div style={{ fontSize: 11, color: T.muted, marginBottom: 4 }}>Message</div>
            <textarea
              value={body}
              maxLength={MAX_BODY}
              rows={6}
              aria-label="Message"
              onChange={event => setBody(event.target.value)}
              style={{ width: '100%' }}
            />
            <div style={{ fontSize: 11, color: T.muted, marginTop: 4 }}>{body.trim().length}/{MAX_BODY}</div>
          </label>
          {error && <p role="alert" style={{ color: T.red, fontSize: 13 }}>{error}</p>}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <Btn
              primary
              disabled={busy || !subject.trim() || !body.trim()}
              onClick={sendMessage}
            >
              {busy ? 'Sending…' : 'Send'}
            </Btn>
            <Btn disabled={busy} onClick={() => { setShowComposer(false); setError(''); }}>Cancel</Btn>
          </div>
        </div>
      )}

      <h4 style={{ fontSize: 11, color: T.muted, textTransform: 'uppercase', letterSpacing: 1, margin: '0 0 8px' }}>
        Sent messages
      </h4>
      {loadingHistory ? (
        <p style={{ color: T.muted, fontSize: 13 }}>Loading sent messages…</p>
      ) : historyError ? (
        <div>
          <p role="alert" style={{ color: T.red, fontSize: 13 }}>{historyError}</p>
          <Btn onClick={loadHistory}>Retry</Btn>
        </div>
      ) : !messages.length ? (
        <p style={{ color: T.muted, fontSize: 13 }}>No messages sent yet.</p>
      ) : (
        <div style={{ display: 'grid', gap: 8 }}>
          {messages.map(message => {
            const expanded = expandedId === message.id;
            return (
              <div key={message.id} style={{ background: T.surface, borderRadius: 8, padding: 10, border: `1px solid ${T.faint}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'start' }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 13 }}>{message.subject}</div>
                    <div style={{ fontSize: 12, color: T.muted, marginTop: 4 }}>
                      {message.createdAtDisplay || message.createdAt}
                    </div>
                  </div>
                  <span style={{ fontSize: 11, color: message.isRead ? T.green : T.orange, whiteSpace: 'nowrap' }}>
                    {message.isRead ? 'Read' : 'Unread'}
                    {message.readAtDisplay ? ` · ${message.readAtDisplay}` : ''}
                  </span>
                </div>
                <Btn
                  style={{ marginTop: 8, fontSize: 12, padding: '6px 10px' }}
                  onClick={() => setExpandedId(expanded ? '' : message.id)}
                >
                  {expanded ? 'Hide message' : 'View message'}
                </Btn>
                {expanded && (
                  <pre style={{
                    whiteSpace: 'pre-wrap',
                    fontFamily: T.font,
                    fontSize: 13,
                    marginTop: 10,
                    marginBottom: 0,
                    color: T.text,
                  }}>
                    {message.body}
                  </pre>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
