import { T } from '../../constants/tokens.js';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';

export default function TodayTab({
  modules,
  completed,
  pct,
  todayComplete,
  countdown,
  isWeeklyDay,
  hasNasaTLX,
  onNavigate,
  sessionBlockMessage,
  cognitiveOverloadIndex,
}) {
  const sessionsBlocked = !!sessionBlockMessage;
  return (
    <div className="fade-in">
      {sessionsBlocked ? (
        <Card style={{marginBottom:14,background:"rgba(252,129,129,0.08)",border:"1px solid rgba(252,129,129,0.35)"}}>
          <div style={{fontWeight:600,fontSize:14,color:T.red,marginBottom:8}}>Today's session is unavailable</div>
          <div style={{fontSize:13,color:T.muted,lineHeight:1.7}}>{sessionBlockMessage}</div>
        </Card>
      ) : null}
      {/* Today status */}
      <Card style={{marginBottom:14}}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:10}}>
          <div>
            <div style={{fontWeight:600,fontSize:15}}>Today's Protocol</div>
            <div style={{fontSize:12,color:T.muted,marginTop:2}}>Target: 2–3 minutes · {new Date().toLocaleDateString("en-US",{weekday:"long",month:"long",day:"numeric"})}</div>
          </div>
          <div style={{fontSize:28,fontWeight:700,color:todayComplete?T.green:T.teal}}>{pct}%</div>
        </div>
        <div style={{background:T.faint,borderRadius:999,height:8,marginBottom:8}}>
          <div style={{background:`linear-gradient(90deg,${T.teal},${T.blue})`,height:8,borderRadius:999,width:`${pct}%`,transition:"width .6s ease"}} />
        </div>
        <div style={{fontSize:12,color:T.muted}}>{completed}/{modules.length} modules complete</div>
      </Card>

      {todayComplete ? (
        <Card style={{textAlign:"center",padding:"28px",marginBottom:14,background:`linear-gradient(135deg,rgba(45,212,191,0.05),rgba(99,179,237,0.05))`,border:`1px solid rgba(45,212,191,0.25)`}}>
          <div style={{fontSize:44,marginBottom:14}}>✅</div>
          <div style={{fontWeight:700,fontSize:19,color:T.teal,marginBottom:8}}>
            Daily Assessment Complete
          </div>
          <div style={{color:T.muted,fontSize:14,lineHeight:1.9,marginBottom:cognitiveOverloadIndex != null ? 16 : 18}}>
            Thank you for contributing to the NeuroCortex study.<br/>
            Please return tomorrow to continue.
          </div>
          {cognitiveOverloadIndex != null ? (
            <div style={{display:"inline-block",background:T.surface,borderRadius:12,padding:"12px 22px",marginBottom:18}}>
              <div style={{fontSize:11,color:T.muted,marginBottom:4,textTransform:"uppercase",letterSpacing:1}}>Cognitive Overload Index</div>
              <div style={{fontFamily:T.mono,fontSize:28,fontWeight:700,color:T.orange}}>{cognitiveOverloadIndex}</div>
            </div>
          ) : null}
          <div style={{display:"inline-block",background:T.surface,borderRadius:12,padding:"12px 22px"}}>
            <div style={{fontSize:11,color:T.muted,marginBottom:4,textTransform:"uppercase",letterSpacing:1}}>Next session available in</div>
            <div style={{fontFamily:T.mono,fontSize:22,fontWeight:700,color:T.blue}}>{countdown}</div>
          </div>
        </Card>
      ) : null}

      <div style={{display:"flex",flexDirection:"column",gap:8,marginBottom:14}}>
        {modules.map(m=>(
          <div key={m.key} style={{background:T.card,border:`1px solid ${m.done?T.teal+"40":T.cardBorder}`,borderRadius:12,padding:"14px 16px",display:"flex",alignItems:"center",gap:14}}>
            <span style={{fontSize:26,width:36,textAlign:"center"}}>{m.icon}</span>
            <div style={{flex:1}}>
              <div style={{fontWeight:500,fontSize:14}}>{m.label}</div>
              <div style={{fontSize:12,color:T.muted}}>{m.time}</div>
            </div>
            {m.done
              ? <span style={{background:"rgba(104,211,145,0.15)",color:T.green,fontSize:12,padding:"4px 12px",borderRadius:20,fontWeight:500}}>✓ Completed</span>
              : sessionsBlocked
                ? <span style={{background:T.surface,color:T.muted,fontSize:12,padding:"4px 12px",borderRadius:20,border:`1px solid ${T.faint}`}}>Unavailable</span>
                : <Btn onClick={()=>onNavigate(m.key)} primary style={{fontSize:13,padding:"8px 16px"}}>Start →</Btn>}
          </div>
        ))}
      </div>

      {isWeeklyDay&&<Card style={{marginBottom:14,border:`1px solid rgba(167,139,250,0.3)`,background:"rgba(167,139,250,0.04)"}}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
          <div>
            <div style={{fontWeight:600,color:T.purple}}>📊 Weekly NASA-TLX Survey</div>
            <div style={{fontSize:12,color:T.muted,marginTop:2}}>Available Fridays · +25 NeuroCoins</div>
          </div>
          {hasNasaTLX
            ?<span style={{background:"rgba(104,211,145,0.15)",color:T.green,fontSize:12,padding:"4px 12px",borderRadius:20}}>✓ Done</span>
            :<Btn onClick={()=>onNavigate("nasatlx")} style={{background:`rgba(167,139,250,0.15)`,color:T.purple,border:`1px solid rgba(167,139,250,0.25)`,padding:"8px 16px",fontSize:13}}>Take Survey</Btn>}
        </div>
      </Card>}
    </div>
  );
}
