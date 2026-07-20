import { useRef, useState } from 'react';
import { T } from '../../constants/tokens.js';
import Store from '../../store/index.js';
import { ApiError } from '../../store/apiClient.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';
import Label from '../ui/Label.jsx';
import ConsentWizard from '../consent/ConsentWizard.jsx';

export default function RegisterScreen({onRegister,onBack,showToast}) {
  const [role,setRole]=useState('participant');
  const [resCode,setResCode]=useState('');
  const [formError,setFormError]=useState('');
  const [loading,setLoading]=useState(false);
  const submitLock=useRef(false);

  const submitResearcher=async event=>{
    event?.preventDefault?.();
    if (loading) return;
    setFormError('');
    if (!resCode.trim()) return setFormError('Please enter your access code.');
    setLoading(true);
    try {
      await onRegister(await Store.loginResearcher({inviteCode:resCode}));
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : error?.message || 'Researcher sign-in failed. Please try again.');
    } finally { setLoading(false); }
  };

  const submitParticipant=async body=>{
    if (submitLock.current) return;
    submitLock.current=true;
    setLoading(true);
    setFormError('');
    try {
      const profile=await Store.registerParticipant(body);
      showToast?.(`Your assent and parent/guardian permission were recorded. Your Participant ID is ${profile.id}. Save this ID for sign-in.`, 'success');
      await onRegister(profile);
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : error?.message || 'Registration failed. Please try again.');
      throw error;
    } finally {
      submitLock.current=false;
      setLoading(false);
    }
  };

  return (
    <Page title="Join the Study" onBack={onBack}>
      <div style={{maxWidth:680,margin:'0 auto 16px',display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}>
        {[['participant','🎓','Participant','Student in the study'],['researcher','🔬','Researcher','Study administrator']].map(([value,icon,label,description])=>(
          <button key={value} onClick={()=>{setRole(value);setFormError('');}} style={{border:`2px solid ${role===value?T.teal:T.faint}`,borderRadius:12,padding:16,background:role===value?'rgba(45,212,191,.06)':'transparent',color:T.text}}>
            <div style={{fontSize:28}}>{icon}</div><strong>{label}</strong><div style={{fontSize:12,color:T.muted,marginTop:4}}>{description}</div>
          </button>
        ))}
      </div>
      {role==='participant' ? (
        <ConsentWizard registration onSubmit={submitParticipant} submitting={loading} error={formError} />
      ) : (
        <Card style={{maxWidth:460,margin:'0 auto'}} className="fade-in">
          <SectionTitle>Researcher sign-in</SectionTitle>
          <form onSubmit={submitResearcher}>
            <Label>Researcher Access Code</Label>
            <input type="password" value={resCode} onChange={e=>{setResCode(e.target.value);setFormError('');}} placeholder="Enter access code (case-insensitive)" disabled={loading} autoComplete="current-password" />
            <p style={{fontSize:11,color:T.muted,marginTop:6,lineHeight:1.6}}>Code is case-insensitive. Contact the study coordinator.</p>
            {formError&&<div role="alert" style={{background:'rgba(252,129,129,.12)',border:'1px solid rgba(252,129,129,.35)',borderRadius:8,padding:'9px 13px',color:T.red,fontSize:13,marginTop:10}}>{formError}</div>}
            <Btn type="submit" primary style={{width:'100%',marginTop:20,padding:13}} disabled={loading}>{loading?'Signing in...':'Sign In as Researcher →'}</Btn>
          </form>
        </Card>
      )}
    </Page>
  );
}
