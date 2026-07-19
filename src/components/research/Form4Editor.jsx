import { T } from '../../constants/tokens.js';
import Btn from '../ui/Btn.jsx';
import Label from '../ui/Label.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';

const TRI_STATE_OPTIONS = [
  { value: '', label: 'Unanswered' },
  { value: 'yes', label: 'Yes' },
  { value: 'no', label: 'No' },
  { value: 'not_applicable', label: 'Not applicable' },
];

const SIGNER_ROLES = [
  'Medical or Mental Health Professional',
  'Educator',
  'School Administrator',
];

function TriStateField({ label, field, form, setForm }) {
  return (
    <div>
      <Label>{label}</Label>
      <select
        value={form[field] ?? ''}
        onChange={e => setForm(prev => ({ ...prev, [field]: e.target.value || null }))}
        style={{ width: '100%', marginBottom: 10 }}
      >
        {TRI_STATE_OPTIONS.map(option => (
          <option key={option.value || 'blank'} value={option.value}>{option.label}</option>
        ))}
      </select>
    </div>
  );
}

function BoolField({ label, field, form, setForm }) {
  return (
    <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 12, marginBottom: 8 }}>
      <input
        type="checkbox"
        checked={form[field] === true}
        onChange={e => setForm(prev => ({ ...prev, [field]: e.target.checked ? true : null }))}
      />
      <span>{label}</span>
    </label>
  );
}

export default function Form4Editor({ form, setForm, documentStatus, onSave, onApprove, onCancel, busy }) {
  const signers = form.signer_records || SIGNER_ROLES.map(role => ({ role, printed_name: '', degree_or_license: '', approval_date: '', signature_status: 'pending' }));

  const updateSigner = (index, key, value) => {
    setForm(prev => {
      const next = [...(prev.signer_records || signers)];
      next[index] = { ...next[index], [key]: value };
      return { ...prev, signer_records: next };
    });
  };

  return (
    <div style={{ marginTop: 12, display: 'grid', gap: 12 }}>
      <SectionTitle>A. Student Researcher / Adult Sponsor</SectionTitle>
      {[
        ['project_title', 'Project title'],
        ['student_researcher_names', 'Student researcher name(s)'],
        ['adult_sponsor', 'Adult sponsor'],
        ['adult_sponsor_contact', 'Phone / email'],
      ].map(([field, label]) => (
        <div key={field}>
          <Label>{label}</Label>
          <input
            value={form[field] ?? ''}
            onChange={e => setForm(prev => ({ ...prev, [field]: e.target.value }))}
            style={{ width: '100%', padding: '8px 10px', fontSize: 12 }}
          />
        </div>
      ))}

      <BoolField label="Research plan submitted" field="research_plan_submitted" form={form} setForm={setForm} />
      <BoolField label="Surveys or questionnaires attached" field="surveys_attached" form={form} setForm={setForm} />
      <BoolField label="Published instruments legally obtained" field="published_instruments_legally_obtained" form={form} setForm={setForm} />
      <BoolField label="Informed consent attached" field="informed_consent_attached" form={form} setForm={setForm} />
      <BoolField label="Working with a Qualified Scientist" field="qualified_scientist" form={form} setForm={setForm} />

      <div style={{ borderTop: `1px solid ${T.faint}`, paddingTop: 12 }}>
        <SectionTitle>B. IRB Use Only</SectionTitle>
        <p style={{ color: T.orange, fontSize: 12, lineHeight: 1.7, marginBottom: 12 }}>
          Complete only from an actual IRB determination. Generating this PDF does not constitute approval.
        </p>
        <BoolField label="Approved with Full Committee Review" field="full_committee_review" form={form} setForm={setForm} />
        <Label>Risk level</Label>
        <select
          value={form.risk_level ?? ''}
          onChange={e => setForm(prev => ({ ...prev, risk_level: e.target.value || null }))}
          style={{ width: '100%', marginBottom: 10 }}
        >
          <option value="">Unanswered</option>
          <option value="minimal">Minimal risk</option>
          <option value="more_than_minimal">More than minimal risk</option>
        </select>
        <BoolField label="Qualified Scientist required" field="qualified_scientist_required" form={form} setForm={setForm} />
        <BoolField label="Risk Assessment required" field="risk_assessment_required" form={form} setForm={setForm} />
        <TriStateField label="Written Minor Assent required" field="minor_assent_required" form={form} setForm={setForm} />
        <TriStateField label="Written Parental Permission required" field="parental_permission_required" form={form} setForm={setForm} />
        <TriStateField label="Written Informed Consent required (18+)" field="adult_informed_consent_required" form={form} setForm={setForm} />
      </div>

      <div style={{ borderTop: `1px solid ${T.faint}`, paddingTop: 12 }}>
        <SectionTitle>Signer Records (printed names only)</SectionTitle>
        {signers.map((signer, index) => (
          <div key={signer.role} style={{ display: 'grid', gap: 8, marginBottom: 12, background: T.surface, padding: 10, borderRadius: 8 }}>
            <div style={{ fontSize: 12, fontWeight: 600 }}>{signer.role}</div>
            <input placeholder="Printed name" value={signer.printed_name || ''} onChange={e => updateSigner(index, 'printed_name', e.target.value)} style={{ padding: '8px 10px', fontSize: 12 }} />
            <input placeholder="Degree / professional license" value={signer.degree_or_license || ''} onChange={e => updateSigner(index, 'degree_or_license', e.target.value)} style={{ padding: '8px 10px', fontSize: 12 }} />
            <input placeholder="Approval date (YYYY-MM-DD)" value={signer.approval_date || ''} onChange={e => updateSigner(index, 'approval_date', e.target.value)} style={{ padding: '8px 10px', fontSize: 12 }} />
            <input placeholder="Signature status" value={signer.signature_status || 'pending'} onChange={e => updateSigner(index, 'signature_status', e.target.value)} style={{ padding: '8px 10px', fontSize: 12 }} />
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <Btn onClick={onSave} primary disabled={busy}>Save Form 4</Btn>
        {documentStatus !== 'approved' ? (
          <Btn onClick={onApprove} disabled={busy || documentStatus === 'draft'} style={{ color: T.orange }}>
            Mark Approved (requires confirmation)
          </Btn>
        ) : null}
        <Btn onClick={onCancel} disabled={busy}>Close</Btn>
      </div>
    </div>
  );
}
