import { useState } from 'react';
import { T } from '../../constants/tokens.js';
import Store from '../../store/index.js';
import { PET_TYPES } from '../../constants/gamification.js';
import { ApiError } from '../../store/apiClient.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';
import Label from '../ui/Label.jsx';

const MINOR_RANGES = new Set(['13-14', '15-16']);
const ADULT_RANGES = new Set(['19-20', '21-22', '23+']);
const AMBIGUOUS_RANGES = new Set(['17-18']);

function resolveEnrollmentCategory(ageRange, ageConsentCategory) {
  if (ageConsentCategory) return ageConsentCategory;
  if (MINOR_RANGES.has(ageRange)) return 'under_18';
  if (ADULT_RANGES.has(ageRange)) return 'age_18_or_over';
  return '';
}

export default function RegisterScreen({onRegister,onBack}) {
  const [role,setRole]=useState("participant");
  const [grade,setGrade]=useState("");
  const [ageRange,setAgeRange]=useState("");
  const [ageConsentCategory,setAgeConsentCategory]=useState("");
  const [resCode,setResCode]=useState("");
  const [petChoice,setPetChoice]=useState("fox");
  const [pin,setPin]=useState("");
  const [step,setStep]=useState(1);
  const [formError,setFormError]=useState("");
  const [loading,setLoading]=useState(false);
  const [assentAck,setAssentAck]=useState(false);
  const [parentalStatus,setParentalStatus]=useState("pending");
  const [adultConsent,setAdultConsent]=useState(false);
  const enrollmentCategory = resolveEnrollmentCategory(ageRange, ageConsentCategory);
  const isMinor = enrollmentCategory === 'under_18';
  const needsCategorySelection = AMBIGUOUS_RANGES.has(ageRange);

  const submitResearcher=async (event)=>{
    event?.preventDefault?.();
    if (loading) return;
    setFormError("");
    if (!resCode.trim()) {
      setFormError("Please enter your access code.");
      return;
    }
    setLoading(true);
    try {
      const profile = await Store.loginResearcher({ inviteCode: resCode });
      await onRegister(profile);
    } catch (error) {
      const message = error instanceof ApiError
        ? error.message
        : error?.message || 'Researcher sign-in failed. Please try again.';
      setFormError(message);
    } finally {
      setLoading(false);
    }
  };

  const submit=async ()=>{
    setFormError("");
    if(role==="researcher"){
      await submitResearcher();
      return;
    }
    if(!grade){setFormError("Please select your grade level."); return;}
    if(!ageRange){setFormError("Please select your age range."); return;}
    if(needsCategorySelection && !ageConsentCategory){
      setFormError("Please confirm whether you are under 18 or 18 years old or over."); return;
    }
    if(!/^\d{4,6}$/.test(pin)){
      setFormError("PIN must be 4–6 digits."); return;
    }
    if(isMinor){
      if(!assentAck){ setFormError("Please confirm participant assent to continue."); return; }
    } else if(enrollmentCategory === 'age_18_or_over'){
      if(!adultConsent){ setFormError("Please confirm the adult informed-consent acknowledgment."); return; }
    } else {
      setFormError("Enrollment category must be resolved before continuing."); return;
    }

    setLoading(true);
    try {
      const profile = await Store.registerParticipant({
        grade,
        ageRange,
        ageConsentCategory: enrollmentCategory || undefined,
        petChoice,
        pin,
        assentAcknowledged: isMinor ? assentAck : undefined,
        parentalPermissionStatus: isMinor ? parentalStatus : undefined,
        adultConsentAcknowledged: isMinor ? undefined : adultConsent,
      });
      await Store.ensureGame(profile.id, petChoice);
      onRegister(profile);
    } catch (error) {
      const message = error instanceof ApiError
        ? error.message
        : error?.message || 'Registration failed. Please try again.';
      setFormError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Page title="Join the Study" onBack={onBack}>
      {step===1&&(
        <Card style={{maxWidth:460,margin:"0 auto"}} className="fade-in">
          <SectionTitle>Choose your role</SectionTitle>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12,marginBottom:20}}>
            {[["participant","🎓","Participant","Student in the study"],["researcher","🔬","Researcher","Study administrator"]].map(([v,e,l,d])=>(
              <div key={v} onClick={()=>setRole(v)} style={{border:`2px solid ${role===v?T.teal:T.faint}`,borderRadius:12,padding:"16px",cursor:"pointer",background:role===v?`rgba(45,212,191,0.06)`:"transparent",transition:"all .2s",textAlign:"center"}}>
                <div style={{fontSize:28,marginBottom:8}}>{e}</div>
                <div style={{fontWeight:600,fontSize:14,color:role===v?T.teal:T.text}}>{l}</div>
                <div style={{fontSize:12,color:T.muted,marginTop:4}}>{d}</div>
              </div>
            ))}
          </div>
          {role==="participant"&&<>
            <Label>Grade Level</Label>
            <select value={grade} onChange={e=>setGrade(e.target.value)} style={{marginBottom:14}}>
              <option value="">Select grade level</option>
              {["9th Grade","10th Grade","11th Grade","12th Grade","College Freshman","College Sophomore","College Junior","College Senior"].map(g=><option key={g}>{g}</option>)}
            </select>
            <Label>Age Range</Label>
            <select value={ageRange} onChange={e=>{setAgeRange(e.target.value); setAgeConsentCategory("");}} style={{marginBottom: needsCategorySelection ? 14 : 0}}>
              <option value="">Select age range</option>
              {["13-14","15-16","17-18","19-20","21-22","23+"].map(a=><option key={a}>{a}</option>)}
            </select>
            {needsCategorySelection ? (
              <>
                <Label>Consent Category</Label>
                <select value={ageConsentCategory} onChange={e=>setAgeConsentCategory(e.target.value)} style={{marginBottom: 0}}>
                  <option value="">Select one option</option>
                  <option value="under_18">I am under 18 years old</option>
                  <option value="age_18_or_over">I am 18 years old or over</option>
                </select>
              </>
            ) : null}
          </>}
          {role==="researcher"&&(
            <form onSubmit={submitResearcher} style={{marginTop:4}}>
              <Label>Researcher Access Code</Label>
              <input type="password" value={resCode}
                onChange={e=>{setResCode(e.target.value);setFormError("");}}
                placeholder="Enter access code (case-insensitive)"
                disabled={loading}
                autoComplete="current-password" />
              <p style={{fontSize:11,color:T.muted,marginTop:6,lineHeight:1.6}}>
                Code is case-insensitive. Contact the study coordinator.
              </p>
              {formError&&(
                <div style={{background:"rgba(252,129,129,0.12)",border:"1px solid rgba(252,129,129,0.35)",borderRadius:8,padding:"9px 13px",color:T.red,fontSize:13,marginTop:10}}>
                  {formError}
                </div>
              )}
              <Btn type="submit" primary style={{width:"100%",marginTop:20,padding:"13px"}} disabled={loading}>
                {loading ? 'Signing in...' : 'Sign In as Researcher →'}
              </Btn>
            </form>
          )}
          {role==="participant"&&formError&&(
            <div style={{background:"rgba(252,129,129,0.12)",border:"1px solid rgba(252,129,129,0.35)",borderRadius:8,padding:"9px 13px",color:T.red,fontSize:13,marginTop:10}}>
              {formError}
            </div>
          )}
          {role==="participant"&&(
            <Btn onClick={()=>setStep(2)} primary style={{width:"100%",marginTop:20,padding:"13px"}} disabled={loading}>
              Choose Study Companion →
            </Btn>
          )}
        </Card>
      )}
      {step===2&&(
        <Card style={{maxWidth:460,margin:"0 auto"}} className="fade-in">
          <SectionTitle>Choose your study companion</SectionTitle>
          <p style={{color:T.muted,fontSize:13,marginBottom:20,lineHeight:1.7}}>Your companion will grow as you complete daily sessions. They need your consistency to thrive!</p>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12,marginBottom:24}}>
            {Object.entries(PET_TYPES).map(([k,p])=>(
              <div key={k} onClick={()=>setPetChoice(k)} style={{border:`2px solid ${petChoice===k?p.color:T.faint}`,borderRadius:12,padding:"18px 14px",cursor:"pointer",background:petChoice===k?`${p.color}10`:"transparent",transition:"all .2s",textAlign:"center"}}>
                <div style={{fontSize:36,marginBottom:8}}>{p.emoji}</div>
                <div style={{fontWeight:600,fontSize:14,color:petChoice===k?p.color:T.text}}>{p.name}</div>
                <div style={{fontSize:11,color:T.muted,marginTop:4}}>{p.desc}</div>
              </div>
            ))}
          </div>
          <div style={{display:"flex",gap:12}}>
            <Btn onClick={()=>setStep(1)} style={{flex:1,padding:"12px"}} disabled={loading}>← Back</Btn>
            <Btn onClick={()=>setStep(3)} primary style={{flex:2,padding:"12px"}} disabled={loading}>
              Continue to Enrollment Acknowledgment →
            </Btn>
          </div>
        </Card>
      )}
      {step===3&&(
        <Card style={{maxWidth:460,margin:"0 auto"}} className="fade-in">
          <SectionTitle>Daily Cognitive Research Enrollment</SectionTitle>
          <p style={{color:T.muted,fontSize:13,lineHeight:1.8,marginBottom:16}}>
            This platform supports anonymous daily wellness and cognitive research check-ins.
            It is not a medical or diagnostic tool.
          </p>
          {isMinor ? (
            <>
              <label style={{display:"flex",gap:10,alignItems:"flex-start",fontSize:13,marginBottom:14}}>
                <input type="checkbox" checked={assentAck} onChange={e=>setAssentAck(e.target.checked)} />
                <span>I agree to participate in this research study and understand I may stop at any time.</span>
              </label>
              <Label>Parental Permission Status</Label>
              <select value={parentalStatus} onChange={e=>setParentalStatus(e.target.value)} style={{marginBottom:8}}>
                <option value="pending">Not yet verified by research team</option>
                <option value="declined">Declined</option>
              </select>
              <p style={{fontSize:12,color:T.muted,lineHeight:1.6,marginBottom:14}}>
                Parental permission has not yet been verified. A researcher must confirm parental permission before sessions can begin.
              </p>
            </>
          ) : (
            <label style={{display:"flex",gap:10,alignItems:"flex-start",fontSize:13,marginBottom:14}}>
              <input type="checkbox" checked={adultConsent} onChange={e=>setAdultConsent(e.target.checked)} />
              <span>I acknowledge the adult informed-consent requirements for this research study and agree to participate voluntarily.</span>
            </label>
          )}
          <Label>Create a PIN (4–6 digits)</Label>
          <input
            type="password"
            inputMode="numeric"
            maxLength={6}
            value={pin}
            onChange={e=>{setPin(e.target.value.replace(/\D/g,''));setFormError("");}}
            placeholder="Enter PIN for sign-in"
            style={{marginBottom:14,letterSpacing:4,fontFamily:T.mono}}
          />
          {formError&&(
            <div style={{background:"rgba(252,129,129,0.12)",border:"1px solid rgba(252,129,129,0.35)",borderRadius:8,padding:"9px 13px",color:T.red,fontSize:13,marginBottom:10}}>
              {formError}
            </div>
          )}
          <div style={{display:"flex",gap:12}}>
            <Btn onClick={()=>setStep(2)} style={{flex:1,padding:"12px"}} disabled={loading}>← Back</Btn>
            <Btn onClick={submit} primary style={{flex:2,padding:"12px"}} disabled={loading}>
              {loading ? 'Registering…' : 'Complete Enrollment →'}
            </Btn>
          </div>
          <p style={{fontSize:11,color:T.muted,marginTop:12,lineHeight:1.7,textAlign:"center"}}>Your anonymous ID is generated automatically.<br/>We collect only grade and age range — no names or contact information.</p>
        </Card>
      )}
    </Page>
  );
}
