import { useEffect, useState } from 'react';
import { T } from '../../constants/tokens.js';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';
import {
  fetchMyConsentStatus,
  requestDataDeletion,
  withdrawParticipation,
} from '../../store/consent.js';

function statusColor(value) {
  if (value === 'granted' || value === 'active') return T.teal;
  if (value === 'withdrawn' || value === 'declined') return T.red;
  return T.muted;
}

export default function ConsentStatusTab({ showToast }) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [confirmWithdraw, setConfirmWithdraw] = useState(false);
  const [confirmDeletion, setConfirmDeletion] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      setStatus(await fetchMyConsentStatus());
    } catch (err) {
      showToast?.(err.message || 'Could not load enrollment status');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const onWithdraw = async () => {
    setBusy(true);
    try {
      setStatus(await withdrawParticipation());
      setConfirmWithdraw(false);
      showToast?.('You have withdrawn from the study.');
    } catch (err) {
      showToast?.(err.message || 'Withdrawal failed');
    } finally {
      setBusy(false);
    }
  };

  const onDeletionRequest = async () => {
    setBusy(true);
    try {
      setStatus(await requestDataDeletion());
      setConfirmDeletion(false);
      showToast?.('Data deletion request recorded.');
    } catch (err) {
      showToast?.(err.message || 'Request failed');
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return <Card><p style={{ color: T.muted, textAlign: 'center', padding: '2rem', fontSize: 14 }}>Loading enrollment status…</p></Card>;
  }

  if (!status) {
    return <Card><p style={{ color: T.muted, textAlign: 'center', padding: '2rem', fontSize: 14 }}>Enrollment status unavailable.</p></Card>;
  }

  const rows = [
    status.age_category === 'minor' && { label: 'Participant assent', value: status.assent_status },
    status.age_category === 'minor' && {
      label: 'Parental permission',
      value: status.parental_permission_status === 'pending' ? 'not yet verified' : status.parental_permission_status,
    },
    status.age_category === 'adult' && { label: 'Adult informed consent', value: status.adult_consent_status },
    { label: 'Age consent category', value: status.age_consent_category },
    { label: 'Protocol version', value: status.protocol_version },
    { label: 'Session eligible', value: status.session_eligible ? 'yes' : 'no' },
    { label: 'Withdrawal status', value: status.withdrawal_status },
  ].filter(Boolean);

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <Card>
        <SectionTitle>Research Enrollment</SectionTitle>
        <p style={{ fontSize: 13, color: T.muted, marginBottom: 16, lineHeight: 1.5 }}>
          This page shows your voluntary research enrollment status. It is not a medical or diagnostic record.
        </p>
        <div style={{ display: 'grid', gap: 10 }}>
          {rows.map(row => (
            <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 13 }}>
              <span style={{ color: T.muted }}>{row.label}</span>
              <span style={{ color: statusColor(row.value), fontWeight: 600, textTransform: 'capitalize' }}>{row.value}</span>
            </div>
          ))}
        </div>
        {!status.session_eligible && status.session_block_message && (
          <div style={{ marginTop: 16, padding: 12, borderRadius: 8, background: `${T.red}15`, color: T.red, fontSize: 12 }}>
            Sessions are currently unavailable: {status.session_block_message}
          </div>
        )}
      </Card>

      {status.withdrawal_status !== 'withdrawn' && (
        <Card>
          <SectionTitle>Withdraw From Study</SectionTitle>
          <p style={{ fontSize: 13, color: T.muted, marginBottom: 12, lineHeight: 1.5 }}>
            You may stop participating at any time. Existing study records are retained according to the active protocol.
          </p>
          {!confirmWithdraw ? (
            <Btn onClick={() => setConfirmWithdraw(true)} style={{ color: T.red, borderColor: `${T.red}55` }}>
              Withdraw from study
            </Btn>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <p style={{ fontSize: 13, color: T.red }}>Confirm withdrawal? You can contact the research team if you wish to rejoin later.</p>
              <div style={{ display: 'flex', gap: 8 }}>
                <Btn primary onClick={onWithdraw} disabled={busy}>Confirm withdrawal</Btn>
                <Btn onClick={() => setConfirmWithdraw(false)} disabled={busy}>Cancel</Btn>
              </div>
            </div>
          )}
        </Card>
      )}

      {!status.deletion_requested && (
        <Card>
          <SectionTitle>Request Data Deletion</SectionTitle>
          <p style={{ fontSize: 13, color: T.muted, marginBottom: 12, lineHeight: 1.5 }}>
            You may request deletion of your research data. The research team will review the request under the active protocol.
          </p>
          {!confirmDeletion ? (
            <Btn onClick={() => setConfirmDeletion(true)}>Request data deletion</Btn>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <p style={{ fontSize: 13, color: T.muted }}>Submit a deletion request to the research team?</p>
              <div style={{ display: 'flex', gap: 8 }}>
                <Btn primary onClick={onDeletionRequest} disabled={busy}>Submit request</Btn>
                <Btn onClick={() => setConfirmDeletion(false)} disabled={busy}>Cancel</Btn>
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
