import { useState, useMemo } from 'react';
import { T } from '../../constants/tokens.js';
import Store from '../../store/index.js';
import { ApiError } from '../../store/apiClient.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';
import Label from '../ui/Label.jsx';

export default function LoginScreen({onLogin,onBack}) {
  const [id,setId]=useState("");
  const [pin,setPin]=useState("");
  const [loginError,setLoginError]=useState("");
  const [loading,setLoading]=useState(false);
  const recentParticipants=useMemo(()=>
    Store.getLocalParticipants().filter(p=>p.role!=="researcher").slice(-6).reverse()
  ,[]);

  const submit=async ()=>{
    setLoginError("");
    const pid=id.trim().toUpperCase();
    if(!pid){setLoginError("Please enter your Participant ID.");return;}
    if(!/^\d{4,6}$/.test(pin)){
      setLoginError("Please enter your 4–6 digit PIN.");
      return;
    }

    setLoading(true);
    try {
      const profile = await Store.loginParticipant({ publicId: pid, pin });
      onLogin(profile);
    } catch (error) {
      const message = error instanceof ApiError
        ? error.message
        : error?.message || 'Sign in failed. Please try again.';
      setLoginError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Page title="Sign In" onBack={onBack}>
      <Card style={{maxWidth:420,margin:"0 auto"}} className="fade-in">
        <SectionTitle>Enter your Participant ID</SectionTitle>
        <input value={id}
          onChange={e=>{setId(e.target.value.toUpperCase());setLoginError("");}}
          placeholder="NC-XXXXXXXXXXXXXXXX"
          style={{fontFamily:T.mono,fontSize:15,marginBottom:14,letterSpacing:2}} />
        <Label>PIN</Label>
        <input
          type="password"
          inputMode="numeric"
          maxLength={6}
          value={pin}
          onChange={e=>{setPin(e.target.value.replace(/\D/g,''));setLoginError("");}}
          onKeyDown={e=>e.key==="Enter"&&submit()}
          placeholder="4–6 digit PIN"
          style={{fontFamily:T.mono,fontSize:15,marginBottom:6,letterSpacing:4}}
        />
        {loginError&&(
          <div style={{background:"rgba(252,129,129,0.12)",border:"1px solid rgba(252,129,129,0.35)",borderRadius:8,padding:"9px 13px",color:T.red,fontSize:13,marginBottom:10}}>
            {loginError}
          </div>
        )}
        <Btn onClick={submit} primary style={{width:"100%",padding:"13px",marginTop:4}} disabled={loading}>
          {loading ? 'Signing in…' : 'Sign In →'}
        </Btn>
        {recentParticipants.length>0&&<>
          <div style={{fontSize:12,color:T.muted,margin:"20px 0 10px",textAlign:"center"}}>Recent participants on this device:</div>
          <div style={{display:"flex",flexDirection:"column",gap:6}}>
            {recentParticipants.map(p=>(
              <button key={p.id} onClick={()=>{setId(p.id);setLoginError("");}}
                style={{background:T.surface,border:`1px solid ${T.faint}`,borderRadius:8,padding:"10px 14px",color:T.text,fontSize:13,textAlign:"left",display:"flex",justifyContent:"space-between",alignItems:"center",cursor:"pointer"}}>
                <span style={{fontFamily:T.mono,fontSize:12,color:T.teal}}>{p.id}</span>
                <span style={{color:T.muted,fontSize:11}}>{p.grade??"—"}{p.ageRange?" · "+p.ageRange:""}</span>
              </button>
            ))}
          </div>
        </>}
      </Card>
    </Page>
  );
}
