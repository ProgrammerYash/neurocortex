import { useEffect, useState } from 'react';
import { T } from '../../constants/tokens.js';
import Btn from '../ui/Btn.jsx';
import {
  fetchParticipantMessages,
  fetchUnreadMessageCount,
  markMessageRead,
} from '../../store/messages.js';

export default function ParticipantInbox({ onBack, onUnreadChange, showToast }) {
  const [messages, setMessages] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [openingId, setOpeningId] = useState('');

  const refreshUnread = () => fetchUnreadMessageCount()
    .then(data => onUnreadChange?.(Number(data.unread_count) || 0))
    .catch(() => {});

  const loadMessages = () => {
    setLoading(true);
    setError('');
    return fetchParticipantMessages()
      .then(data => setMessages(Array.isArray(data.items) ? data.items : []))
      .catch(err => setError(err.message || 'Could not load inbox.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadMessages();
    refreshUnread();
  }, []);

  const openMessage = async message => {
    setOpeningId(message.id);
    try {
      if (!message.isRead) {
        const updated = await markMessageRead(message.id);
        setMessages(prev => prev.map(item => (item.id === message.id ? updated : item)));
        setSelected(updated);
        await refreshUnread();
        return;
      }
      setSelected(message);
    } catch (err) {
      showToast?.(err.message || 'Could not open message.', 'error');
    } finally {
      setOpeningId('');
    }
  };

  if (selected) {
    return (
      <div style={{ maxWidth: 720, margin: '0 auto', padding: '1rem 1rem 4rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', marginBottom: 16 }}>
          <Btn onClick={() => setSelected(null)}>Back to Inbox</Btn>
        </div>
        <div style={{ background: T.card, border: `1px solid ${T.cardBorder}`, borderRadius: 12, padding: 18 }}>
          <div style={{ fontSize: 11, color: T.muted, marginBottom: 6 }}>From NeuroCortex Research Team</div>
          <h1 style={{ fontSize: 20, margin: '0 0 8px' }}>{selected.subject}</h1>
          <div style={{ fontSize: 12, color: T.muted, marginBottom: 16 }}>
            {selected.createdAtDisplay || selected.createdAt}
          </div>
          <pre style={{ whiteSpace: 'pre-wrap', fontFamily: T.font, fontSize: 14, lineHeight: 1.7, margin: 0 }}>
            {selected.body}
          </pre>
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: '1rem 1rem 4rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', marginBottom: 16 }}>
        <div>
          <div style={{ fontSize: 11, color: T.muted, textTransform: 'uppercase', letterSpacing: 1 }}>Inbox</div>
          <h1 style={{ fontSize: 22, margin: '4px 0 0' }}>Messages</h1>
        </div>
        <Btn onClick={onBack}>Back</Btn>
      </div>

      {loading ? (
        <p style={{ color: T.muted }}>Loading messages…</p>
      ) : error ? (
        <div>
          <p role="alert" style={{ color: T.red }}>{error}</p>
          <Btn onClick={loadMessages}>Retry</Btn>
        </div>
      ) : !messages.length ? (
        <p style={{ color: T.muted }}>No messages yet.</p>
      ) : (
        <div style={{ display: 'grid', gap: 10 }}>
          {messages.map(message => (
            <button
              key={message.id}
              type="button"
              onClick={() => openMessage(message)}
              disabled={openingId === message.id}
              style={{
                textAlign: 'left',
                background: T.card,
                border: `1px solid ${message.isRead ? T.faint : T.teal}`,
                borderRadius: 10,
                padding: 14,
                color: T.text,
                cursor: 'pointer',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <strong style={{ fontSize: 14 }}>{message.subject}</strong>
                {!message.isRead && <span style={{ color: T.teal, fontSize: 11 }}>Unread</span>}
              </div>
              <div style={{ fontSize: 12, color: T.muted, marginTop: 6 }}>
                NeuroCortex Research Team · {message.createdAtDisplay || message.createdAt}
              </div>
              <div style={{ fontSize: 13, color: T.muted, marginTop: 8, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {message.body}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
