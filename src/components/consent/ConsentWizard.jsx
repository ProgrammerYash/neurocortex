import { useEffect, useRef, useState } from 'react';
import { T } from '../../constants/tokens.js';
import { fetchCurrentConsent } from '../../store/consent.js';
import { PET_TYPES } from '../../constants/gamification.js';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import Label from '../ui/Label.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';
import ConsentDocument from './ConsentDocument.jsx';
import SignaturePad from './SignaturePad.jsx';

const GRADES = ['9th Grade','10th Grade','11th Grade','12th Grade','College Freshman','College Sophomore','College Junior','College Senior'];
const AGES = ['13-14','15-16','17-18','19-20','21-22','23+'];

export default function ConsentWizard({ registration = false, onSubmit, submitting = false, error = '' }) {
  const [step, setStep] = useState(1);
  const [consent, setConsent] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [account, setAccount] = useState({grade:'', ageRange:'', ageConsentCategory:'', petChoice:'fox', pin:'', pinConfirmation:'', participantPrintedName:'', guardianPrintedName:''});
  const [participantAck, setParticipantAck] = useState(false);
  const [guardianAck, setGuardianAck] = useState(false);
  const [participantSigned, setParticipantSigned] = useState(false);
  const [guardianSigned, setGuardianSigned] = useState(false);
  const [participantSignaturePng, setParticipantSignaturePng] = useState(null);
  const [guardianSignaturePng, setGuardianSignaturePng] = useState(null);
  const participantPad = useRef(null);
  const guardianPad = useRef(null);
  const submitRef = useRef(false);
  const idempotencyKey = useRef(crypto.randomUUID());
  const needsCategory = account.ageRange === '17-18';

  useEffect(() => {
    let active = true;
    fetchCurrentConsent()
      .then(data => active && setConsent(data))
      .catch(err => active && setLoadError(err.message || 'Consent form is unavailable.'));
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!submitting) submitRef.current = false;
  }, [submitting]);

  const namesValid = () => Boolean(account.participantPrintedName.trim() && account.guardianPrintedName.trim());

  const accountValid = () => {
    if (!account.grade || !account.ageRange || !namesValid()) return false;
    if (needsCategory && !account.ageConsentCategory) return false;
    return /^\d{4,6}$/.test(account.pin) && account.pin === account.pinConfirmation;
  };

  const finalSubmit = async () => {
    if (submitRef.current || submitting) return;
    if (!participantAck || !guardianAck || !participantSignaturePng || !guardianSignaturePng) return;
    submitRef.current = true;
    const body = {
      ...(registration ? {
        grade: account.grade,
        ageRange: account.ageRange,
        ageConsentCategory: needsCategory ? account.ageConsentCategory : (['13-14','15-16'].includes(account.ageRange) ? 'under_18' : 'age_18_or_over'),
        petChoice: account.petChoice,
        pin: account.pin,
        pinConfirmation: account.pinConfirmation,
      } : {}),
      participantPrintedName: account.participantPrintedName.trim(),
      guardianPrintedName: account.guardianPrintedName.trim(),
      participantAcknowledged: participantAck,
      guardianAcknowledged: guardianAck,
      participantSignaturePng,
      guardianSignaturePng,
      consentVersion: consent.consent_version,
      surveyVersion: consent.survey_version,
      templateSha256: consent.template_sha256,
      idempotencyKey: idempotencyKey.current,
    };
    try {
      await onSubmit(body);
      participantPad.current?.clear();
      guardianPad.current?.clear();
      setParticipantSignaturePng(null);
      setGuardianSignaturePng(null);
      setParticipantAck(false);
      setGuardianAck(false);
    } catch {
      // The parent displays the safe API error. Keep signatures in memory for retry.
    } finally {
      submitRef.current = false;
    }
  };

  if (loadError) return <Card><p role="alert" style={{color:T.red}}>Consent form unavailable: {loadError}</p></Card>;
  if (!consent) return <Card><p style={{color:T.muted}}>Loading approved consent form…</p></Card>;

  const nav = (back, next, disabled = false, nextLabel = 'Continue →') => (
    <div style={{display:'flex', gap:12, marginTop:20}}>
      {back && <Btn onClick={() => setStep(back)} disabled={submitting} style={{flex:1}}>← Back</Btn>}
      {next && <Btn onClick={() => setStep(next)} disabled={disabled || submitting} primary style={{flex:2}}>{nextLabel}</Btn>}
    </div>
  );

  return (
    <div style={{maxWidth:680, margin:'0 auto'}}>
      <p style={{fontSize:12, color:T.muted, textAlign:'center', marginBottom:10}}>
        Step {step} of 5
      </p>
      {step === 1 && !registration && (
        <Card className="fade-in">
          <SectionTitle>Participant and guardian names</SectionTitle>
          <p style={{fontSize:12, color:T.muted, lineHeight:1.6, marginBottom:14}}>Enter each legal name once. You will review and sign on the following steps.</p>
          <Label>Participant legal printed name</Label><input aria-label="Participant legal printed name" value={account.participantPrintedName} onChange={e=>setAccount(a=>({...a,participantPrintedName:e.target.value}))} style={{marginBottom:12}} autoComplete="name" />
          <Label>Guardian legal printed name</Label><input aria-label="Guardian legal printed name" value={account.guardianPrintedName} onChange={e=>setAccount(a=>({...a,guardianPrintedName:e.target.value}))} style={{marginBottom:12}} autoComplete="name" />
          {nav(null,2,!namesValid(),'Read Consent Form →')}
        </Card>
      )}
      {step === 1 && registration && (
        <Card className="fade-in">
          <SectionTitle>Account, participant, and guardian</SectionTitle>
          <p style={{fontSize:12, color:T.muted, lineHeight:1.6, marginBottom:14}}>Your Participant ID will be generated when enrollment succeeds. Save it with your PIN.</p>
          <Label>Grade Level</Label>
          <select aria-label="Grade Level" value={account.grade} onChange={e=>setAccount(a=>({...a,grade:e.target.value}))} style={{marginBottom:12}}><option value="">Select grade level</option>{GRADES.map(x=><option key={x}>{x}</option>)}</select>
          <Label>Age Range</Label>
          <select aria-label="Age Range" value={account.ageRange} onChange={e=>setAccount(a=>({...a,ageRange:e.target.value,ageConsentCategory:''}))} style={{marginBottom:12}}><option value="">Select age range</option>{AGES.map(x=><option key={x}>{x}</option>)}</select>
          {needsCategory && <><Label>Consent Category</Label><select aria-label="Consent Category" value={account.ageConsentCategory} onChange={e=>setAccount(a=>({...a,ageConsentCategory:e.target.value}))} style={{marginBottom:12}}><option value="">Select one</option><option value="under_18">Under 18</option><option value="age_18_or_over">18 or over</option></select></>}
          <Label>Study Companion</Label>
          <select aria-label="Study Companion" value={account.petChoice} onChange={e=>setAccount(a=>({...a,petChoice:e.target.value}))} style={{marginBottom:12}}>{Object.entries(PET_TYPES).map(([key,pet])=><option key={key} value={key}>{pet.emoji} {pet.name}</option>)}</select>
          <Label>Participant legal printed name</Label><input aria-label="Participant legal printed name" value={account.participantPrintedName} onChange={e=>setAccount(a=>({...a,participantPrintedName:e.target.value}))} style={{marginBottom:12}} autoComplete="name" />
          <Label>Guardian legal printed name</Label><input aria-label="Guardian legal printed name" value={account.guardianPrintedName} onChange={e=>setAccount(a=>({...a,guardianPrintedName:e.target.value}))} style={{marginBottom:12}} autoComplete="name" />
          <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:12}}>
            <div><Label>Create PIN (4–6 digits)</Label><input aria-label="Create PIN" type="password" inputMode="numeric" maxLength={6} value={account.pin} onChange={e=>setAccount(a=>({...a,pin:e.target.value.replace(/\D/g,'')}))} /></div>
            <div><Label>Confirm PIN</Label><input aria-label="Confirm PIN" type="password" inputMode="numeric" maxLength={6} value={account.pinConfirmation} onChange={e=>setAccount(a=>({...a,pinConfirmation:e.target.value.replace(/\D/g,'')}))} /></div>
          </div>
          {nav(null,2,!accountValid(),'Read Consent Form →')}
        </Card>
      )}
      {step === 2 && (
        <Card className="fade-in">
          <SectionTitle>Informed Consent Form</SectionTitle>
          <ConsentDocument consent={consent} />
          {nav(1,3,false,'Participant Review →')}
        </Card>
      )}
      {step === 3 && (
        <Card className="fade-in">
          <SectionTitle>Participant acknowledgment</SectionTitle>
          <p style={{fontSize:13, lineHeight:1.7, marginBottom:14}}>{consent.participant_acknowledgment}</p>
          <p style={{fontSize:13, marginBottom:14}}>Signing as: <strong>{account.participantPrintedName.trim()}</strong></p>
          <label style={{display:'flex', gap:10, fontSize:13, marginBottom:16}}><input aria-label="Participant acknowledgment" type="checkbox" checked={participantAck} onChange={e=>setParticipantAck(e.target.checked)} style={{width:'auto'}} /><span>I have read and agree to the participant acknowledgment above.</span></label>
          <SignaturePad ref={participantPad} label="Participant signature" onChange={setParticipantSigned} />
          <div style={{display:'flex', gap:12, marginTop:20}}>
            <Btn onClick={()=>setStep(2)} style={{flex:1}}>← Back</Btn>
            <Btn onClick={()=>{setParticipantSignaturePng(participantPad.current.toPNG());setStep(4);}} disabled={!participantAck || !participantSigned || !namesValid()} primary style={{flex:2}}>Guardian Review →</Btn>
          </div>
        </Card>
      )}
      {step === 4 && (
        <Card className="fade-in">
          <SectionTitle>Guardian acknowledgment</SectionTitle>
          <p style={{fontSize:13, lineHeight:1.7, marginBottom:14}}>{consent.guardian_acknowledgment}</p>
          <p style={{fontSize:13, marginBottom:14}}>Signing as parent/guardian: <strong>{account.guardianPrintedName.trim()}</strong></p>
          <label style={{display:'flex', gap:10, fontSize:13, marginBottom:16}}><input aria-label="Guardian acknowledgment" type="checkbox" checked={guardianAck} onChange={e=>setGuardianAck(e.target.checked)} style={{width:'auto'}} /><span>I have read and agree to the guardian acknowledgment above.</span></label>
          <SignaturePad ref={guardianPad} label="Guardian signature" onChange={setGuardianSigned} />
          <div style={{display:'flex', gap:12, marginTop:20}}>
            <Btn onClick={()=>{setParticipantSigned(false);setParticipantSignaturePng(null);setGuardianSigned(false);setGuardianSignaturePng(null);setStep(3);}} style={{flex:1}}>← Back</Btn>
            <Btn onClick={()=>{setGuardianSignaturePng(guardianPad.current.toPNG());setStep(5);}} disabled={!guardianAck || !guardianSigned || !namesValid()} primary style={{flex:2}}>Final Review →</Btn>
          </div>
        </Card>
      )}
      {step === 5 && (
        <Card className="fade-in">
          <SectionTitle>Final review and submit</SectionTitle>
          <div style={{fontSize:13, lineHeight:1.9}}>
            <div>Participant: <strong>{account.participantPrintedName.trim()}</strong></div>
            <div>Guardian: <strong>{account.guardianPrintedName.trim()}</strong></div>
            <div>Participant acknowledgment and signature: <strong>Complete</strong></div>
            <div>Guardian acknowledgment and signature: <strong>Complete</strong></div>
            <div>Consent version: <strong>{consent.consent_version}</strong></div>
          </div>
          {error && <p role="alert" style={{color:T.red, marginTop:12, fontSize:13}}>{error}</p>}
          <div style={{display:'flex', gap:12, marginTop:20}}>
            <Btn onClick={()=>{setGuardianSigned(false);setGuardianSignaturePng(null);setStep(4);}} disabled={submitting} style={{flex:1}}>← Back</Btn>
            <Btn onClick={finalSubmit} disabled={submitting} primary style={{flex:2}}>{submitting ? 'Submitting…' : registration ? 'Create Account and Submit Consent' : 'Submit Consent'}</Btn>
          </div>
        </Card>
      )}
    </div>
  );
}
