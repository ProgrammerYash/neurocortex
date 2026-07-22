import { T } from '../../constants/tokens.js';

const FIELDS = [
  ['Student Researcher', 'student_researcher'],
  ['Project Title', 'project_title'],
  ['Purpose', 'purpose'],
  ['What participation involves', 'participation_activities'],
  ['Time required', 'time_required'],
  ['Potential risks', 'potential_risks'],
  ['Potential benefits', 'potential_benefits'],
  ['Confidentiality', 'confidentiality'],
  ['Questions and contact', 'questions_contact'],
  ['Adult sponsor', 'adult_sponsor'],
  ['Adult sponsor contact', 'adult_sponsor_contact'],
  ['Voluntary participation', 'voluntary_participation'],
  ['Right to stop or skip questions', 'participation_rights'],
  ['Signing explanation', 'signing_explanation'],
];

export default function ConsentDocument({ consent }) {
  return (
    <article aria-label="Informed consent document" style={{padding:'4px 2px'}}>
      {FIELDS.map(([label, key]) => (
        <section key={key} style={{marginBottom:16}}>
          <h3 style={{fontSize:13, color:T.teal, marginBottom:5}}>{label}</h3>
          <p style={{fontSize:13, color:T.text, lineHeight:1.75, whiteSpace:'pre-wrap'}}>
            {key === 'participation_rights'
              ? `${consent?.may_stop || ''} ${consent?.may_skip_questions || ''}`.trim()
              : consent?.[key]}
          </p>
        </section>
      ))}
    </article>
  );
}
