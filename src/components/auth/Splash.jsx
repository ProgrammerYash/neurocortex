import { T } from '../../constants/tokens.js';

export default function Splash() {
  return (
    <div style={{minHeight:"100vh",display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",background:T.bg}}>
      <div className="glow" style={{width:88,height:88,borderRadius:24,background:`linear-gradient(135deg,${T.tealDim},${T.blueDim})`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:44,marginBottom:20}}>🧠</div>
      <div style={{fontWeight:700,fontSize:28,letterSpacing:3,color:T.teal}}>NEUROCORTEX</div>
      <div style={{color:T.muted,fontSize:12,letterSpacing:4,marginTop:6}}>ISEF RESEARCH PLATFORM</div>
      <div className="spin" style={{width:32,height:32,borderRadius:"50%",border:`2px solid ${T.faint}`,borderTopColor:T.teal,marginTop:40}} />
    </div>
  );
}
