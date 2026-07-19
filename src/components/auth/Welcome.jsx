import { T } from '../../constants/tokens.js';
import Btn from '../ui/Btn.jsx';

export default function Welcome({onLogin,onRegister}) {
  return (
    <div style={{minHeight:"100vh",display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",padding:"2rem",background:`radial-gradient(ellipse at 50% 0%, rgba(45,212,191,0.08) 0%, transparent 60%), ${T.bg}`}}>
      <div style={{textAlign:"center",maxWidth:420}}>
        <div className="heartbeat" style={{fontSize:64,marginBottom:24}}>🧠</div>
        <h1 style={{fontSize:36,fontWeight:700,background:`linear-gradient(135deg,${T.teal},${T.blue})`,WebkitBackgroundClip:"text",WebkitTextFillColor:"transparent",marginBottom:8}}>NeuroCortex</h1>
        <p style={{color:T.muted,fontSize:14,lineHeight:1.8,marginBottom:8}}>ISEF Longitudinal Research Platform</p>
        <p style={{color:T.muted,fontSize:13,lineHeight:1.7,marginBottom:36}}>Daily Cognitive Research Session<br/>Anonymous wellness and performance check-ins</p>
        <div style={{display:"flex",flexDirection:"column",gap:12}}>
          <Btn onClick={onRegister} primary style={{padding:"15px",fontSize:15,fontWeight:600}}>Join the Study</Btn>
          <Btn onClick={onLogin} style={{padding:"14px",fontSize:14,background:"rgba(99,179,237,0.08)",color:T.blue,border:`1px solid rgba(99,179,237,0.2)`}}>Sign In with Participant ID</Btn>
        </div>
        <p style={{color:T.muted,fontSize:11,marginTop:28,lineHeight:1.7}}>Anonymous participation · Research use only<br/>No personal data collected · IRB compliant</p>
      </div>
    </div>
  );
}
