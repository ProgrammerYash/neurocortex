import { useEffect, useState } from 'react';
import { T } from '../../constants/tokens.js';
import {
  createForm4Draft,
  downloadDocument,
  fetchDocument,
  fetchDocuments,
  generateForm4Document,
  updateDocumentStatus,
  updateForm4Document,
} from '../../store/documents.js';
import {
  excludeParticipantFromMl,
  fetchEnrollmentStatus,
  includeParticipantInMl,
  recordResearcherConsentEvent,
  resolveAgeConsentCategory,
} from '../../store/consent.js';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';
import Form4Editor from './Form4Editor.jsx';

function statusColor(value) {
  if (value === 'granted' || value === 'active') return T.green;
  if (value === 'withdrawn' || value === 'declined' || value === 'unresolved') return T.red;
  return T.orange;
}

const EMPTY_FORM = {
  project_title: '',
  student_researcher_names: '',
  adult_sponsor: '',
  adult_sponsor_contact: '',
  research_plan_submitted: null,
  surveys_attached: null,
  published_instruments_legally_obtained: null,
  informed_consent_attached: null,
  qualified_scientist: null,
  full_committee_review: null,
  risk_level: null,
  qualified_scientist_required: null,
  risk_assessment_required: null,
  minor_assent_required: null,
  parental_permission_required: null,
  adult_informed_consent_required: null,
  signer_records: [],
};

export default function HumanParticipantsTab() {
  const [enrollment, setEnrollment] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState(null);
  const [editingStatus, setEditingStatus] = useState('draft');
  const [form, setForm] = useState(EMPTY_FORM);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [rows, docs] = await Promise.all([
        fetchEnrollmentStatus().catch(() => []),
        fetchDocuments().catch(() => []),
      ]);
      setEnrollment(Array.isArray(rows) ? rows : []);
      setDocuments(Array.isArray(docs) ? docs : []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const withdrawnOrExcluded = enrollment.filter(
    row => row.withdrawal_status === 'withdrawn' || row.excluded_from_ml || row.deletion_requested,
  );

  const startEdit = async (doc) => {
    setBusy(true);
    setMessage('');
    try {
      const detail = await fetchDocument(doc.id);
      setEditingId(doc.id);
      setEditingStatus(detail.status);
      setForm({ ...EMPTY_FORM, ...(detail.form4 || {}), project_title: detail.form4?.project_title || doc.project_title || '' });
    } catch (e) {
      setMessage(e.message || 'Failed to load Form 4');
    } finally {
      setBusy(false);
    }
  };

  const handleCreateDraft = async () => {
    setMessage('');
    try {
      await createForm4Draft({ project_title: 'NeuroCortex Longitudinal Research Study' });
      setMessage('Form 4 draft created.');
      await load();
    } catch (e) {
      setMessage(e.message || 'Failed to create Form 4 draft');
    }
  };

  const handleSave = async () => {
    if (!editingId) return;
    setBusy(true);
    setMessage('');
    try {
      await updateForm4Document(editingId, form);
      setMessage('Form 4 saved.');
      await load();
      const detail = await fetchDocument(editingId);
      setEditingStatus(detail.status);
    } catch (e) {
      setMessage(e.message || 'Failed to save Form 4');
    } finally {
      setBusy(false);
    }
  };

  const handleApprove = async () => {
    if (!editingId) return;
    if (!window.confirm('Confirm IRB approval status? This requires all IRB fields and signer records to be complete.')) return;
    setBusy(true);
    try {
      await updateForm4Document(editingId, form);
      await updateDocumentStatus(editingId, { status: 'approved', confirm_approved: true });
      setMessage('Document marked approved.');
      setEditingStatus('approved');
      await load();
    } catch (e) {
      setMessage(e.message || 'Approval failed');
    } finally {
      setBusy(false);
    }
  };

  const handleGenerate = async (documentId) => {
    setMessage('');
    try {
      await generateForm4Document(documentId);
      setMessage('PDF generated as administrative draft.');
      await load();
    } catch (e) {
      setMessage(e.message || 'PDF generation failed');
    }
  };

  const handleDownload = async (documentId) => {
    try {
      const blob = await downloadDocument(documentId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'form-4-administrative-draft.pdf';
      link.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setMessage(e.message || 'Download failed');
    }
  };

  const verifyParentalPermission = async (row) => {
    setMessage('');
    try {
      await recordResearcherConsentEvent(row.participant_id, {
        event_type: 'parental_permission_granted',
        status: 'granted',
        form_type: 'parental_permission',
      });
      setMessage(`Parental permission recorded for ${row.participant_id}.`);
      await load();
    } catch (e) {
      setMessage(e.message || 'Researcher override failed');
    }
  };

  const resolveAgeCategory = async (row, category) => {
    setMessage('');
    try {
      await resolveAgeConsentCategory(row.participant_id, category);
      setMessage(`Age consent category resolved for ${row.participant_id}.`);
      await load();
    } catch (e) {
      setMessage(e.message || 'Age category resolution failed');
    }
  };

  const toggleMl = async (row, excluded) => {
    try {
      if (excluded) await includeParticipantInMl(row.participant_id);
      else await excludeParticipantFromMl(row.participant_id);
      await load();
    } catch (e) {
      setMessage(e.message || 'ML exclusion update failed');
    }
  };

  if (loading) {
    return <Card><div style={{ color: T.muted, fontSize: 13 }}>Loading human participants data…</div></Card>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <Card>
        <SectionTitle>Enrollment Status</SectionTitle>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ color: T.muted, textAlign: 'left' }}>
                {['Public ID', 'Age Range', 'Category', 'Assent', 'Parental', 'Adult Consent', 'Protocol', 'Session', 'ML', 'Withdrawal', 'Actions'].map(h => (
                  <th key={h} style={{ padding: '8px 6px' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {enrollment.map(row => (
                <tr key={row.participant_id} style={{ borderTop: `1px solid ${T.faint}` }}>
                  <td style={{ padding: '8px 6px', fontFamily: T.mono }}>{row.participant_id}</td>
                  <td style={{ padding: '8px 6px' }}>{row.age_range}</td>
                  <td style={{ padding: '8px 6px', color: statusColor(row.age_consent_category) }}>{row.age_consent_category}</td>
                  <td style={{ padding: '8px 6px', color: statusColor(row.assent_status) }}>{row.assent_status}</td>
                  <td style={{ padding: '8px 6px', color: statusColor(row.parental_permission_status) }}>{row.parental_permission_status}</td>
                  <td style={{ padding: '8px 6px', color: statusColor(row.adult_consent_status) }}>{row.adult_consent_status}</td>
                  <td style={{ padding: '8px 6px' }}>{row.protocol_version}</td>
                  <td style={{ padding: '8px 6px', color: row.session_eligible ? T.green : T.red }}>{row.session_eligible ? 'yes' : 'no'}</td>
                  <td style={{ padding: '8px 6px', color: row.ml_eligible ? T.green : T.red }}>{row.ml_eligible ? 'yes' : 'no'}</td>
                  <td style={{ padding: '8px 6px', color: statusColor(row.withdrawal_status) }}>{row.withdrawal_status}</td>
                  <td style={{ padding: '8px 6px', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {row.age_consent_category === 'unresolved' ? (
                      <>
                        <button onClick={() => resolveAgeCategory(row, 'under_18')} style={{ fontSize: 11, padding: '4px 8px', borderRadius: 6, border: `1px solid ${T.faint}`, background: T.surface, cursor: 'pointer' }}>
                          Resolve under 18
                        </button>
                        <button onClick={() => resolveAgeCategory(row, 'age_18_or_over')} style={{ fontSize: 11, padding: '4px 8px', borderRadius: 6, border: `1px solid ${T.faint}`, background: T.surface, cursor: 'pointer' }}>
                          Resolve 18+
                        </button>
                      </>
                    ) : null}
                    {row.age_category === 'minor' && row.parental_permission_status !== 'granted' ? (
                      <button onClick={() => verifyParentalPermission(row)} style={{ fontSize: 11, padding: '4px 8px', borderRadius: 6, border: `1px solid ${T.faint}`, background: T.surface, cursor: 'pointer' }}>
                        Verify parental permission
                      </button>
                    ) : null}
                    <button onClick={() => toggleMl(row, row.excluded_from_ml)} style={{ fontSize: 11, padding: '4px 8px', borderRadius: 6, border: `1px solid ${T.faint}`, background: T.surface, cursor: 'pointer' }}>
                      {row.excluded_from_ml ? 'Include ML' : 'Exclude ML'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card>
        <SectionTitle>Form 4 Documents</SectionTitle>
        <p style={{ color: T.orange, fontSize: 12, lineHeight: 1.7, marginBottom: 12 }}>
          Generated documents are administrative drafts unless formally approved by the IRB.
        </p>
        <Btn onClick={handleCreateDraft} style={{ marginBottom: 12 }}>Create Form 4 Draft</Btn>
        {documents.map(doc => (
          <div key={doc.id} style={{ background: T.surface, borderRadius: 8, padding: 12, marginBottom: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
              <div>
                <div style={{ fontWeight: 600 }}>{doc.project_title || 'Untitled Form 4'}</div>
                <div style={{ fontSize: 11, color: T.muted }}>
                  {doc.protocol_version} · {doc.status} · {doc.completion_percentage}% complete
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <Btn onClick={() => startEdit(doc)} style={{ fontSize: 11, padding: '6px 10px' }}>Edit</Btn>
                <Btn onClick={() => handleGenerate(doc.id)} style={{ fontSize: 11, padding: '6px 10px' }}>Generate</Btn>
                <Btn onClick={() => handleDownload(doc.id)} style={{ fontSize: 11, padding: '6px 10px' }} disabled={!doc.has_generated_pdf}>Download</Btn>
              </div>
            </div>
          </div>
        ))}
        {editingId ? (
          <Form4Editor
            form={form}
            setForm={setForm}
            documentStatus={editingStatus}
            onSave={handleSave}
            onApprove={handleApprove}
            onCancel={() => { setEditingId(null); setForm(EMPTY_FORM); }}
            busy={busy}
          />
        ) : null}
      </Card>

      <Card>
        <SectionTitle>Withdrawn / ML-Excluded Participants</SectionTitle>
        {withdrawnOrExcluded.length === 0 ? (
          <div style={{ fontSize: 12, color: T.muted }}>No withdrawn or ML-excluded participants.</div>
        ) : (
          withdrawnOrExcluded.map(row => (
            <div key={row.participant_id} style={{ fontSize: 12, padding: '8px 0', borderTop: `1px solid ${T.faint}` }}>
              <span style={{ fontFamily: T.mono, fontWeight: 600 }}>{row.participant_id}</span>
              {' · '}
              {row.withdrawal_status === 'withdrawn' ? 'withdrawn' : row.excluded_from_ml ? 'ML excluded' : 'deletion requested'}
            </div>
          ))
        )}
      </Card>

      {message ? <Card><div style={{ fontSize: 12, color: T.muted }}>{message}</div></Card> : null}
    </div>
  );
}
