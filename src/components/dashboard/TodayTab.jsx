import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import { useParticipantTokens } from '../participant/ParticipantAppShell.jsx';

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
  studyScheduleLabel,
}) {
  const P = useParticipantTokens();
  const sessionsBlocked = !!sessionBlockMessage;
  return (
    <div className="fade-in">
      {sessionsBlocked ? (
        <Card style={{marginBottom:14,background:"rgba(252,129,129,0.08)",border:"1px solid rgba(252,129,129,0.35)"}}>
          <div style={{fontWeight:600,fontSize:14,color:P.red,marginBottom:8}}>Today's session is unavailable</div>
          <div style={{fontSize:13,color:P.muted,lineHeight:1.7}}>{sessionBlockMessage}</div>
        </Card>
      ) : null}
      {/* Today status */}
      <Card style={{marginBottom:14}}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:10,flexWrap:'wrap',gap:8}}>
          <div>
            <div style={{fontWeight:600,fontSize:15}}>Today's Protocol</div>
            <div style={{fontSize:12,color:P.muted,marginTop:2}}>Target: 2–3 minutes · {new Date().toLocaleDateString("en-US",{weekday:"long",month:"long",day:"numeric"})}</div>
            {studyScheduleLabel ? (
              <div style={{fontSize:12,color:P.teal,marginTop:6}}>Study Schedule: {studyScheduleLabel}</div>
            ) : null}
          </div>
          <div style={{fontSize:28,fontWeight:700,color:todayComplete?P.green:P.teal}}>{pct}%</div>
        </div>
        <div style={{background:P.faint,borderRadius:999,height:8,marginBottom:8}}>
          <div style={{background:`linear-gradient(90deg,${P.teal},${P.blue})`,height:8,borderRadius:999,width:`${pct}%`,transition:"width .6s ease"}} />
        </div>
        <div style={{fontSize:12,color:P.muted}}>{completed}/{modules.length} modules complete</div>
      </Card>

      {todayComplete ? (
        <Card style={{textAlign:"center",padding:"28px",marginBottom:14,background:`linear-gradient(135deg,rgba(45,212,191,0.05),rgba(99,179,237,0.05))`,border:`1px solid rgba(45,212,191,0.25)`}}>
          <div style={{fontSize:44,marginBottom:14}}>✅</div>
          <div style={{fontWeight:700,fontSize:19,color:P.teal,marginBottom:8}}>
            Daily Assessment Complete
          </div>
          <div style={{color:P.muted,fontSize:14,lineHeight:1.9,marginBottom:cognitiveOverloadIndex != null ? 16 : 18}}>
            Thank you for contributing to the NeuroCortex study.<br/>
            Please return tomorrow to continue.
          </div>
          {cognitiveOverloadIndex != null ? (
            <div style={{display:"inline-block",background:P.surface,borderRadius:12,padding:"12px 22px",marginBottom:18}}>
              <div style={{fontSize:11,color:P.muted,marginBottom:4,textTransform:"uppercase",letterSpacing:1}}>Cognitive Overload Index</div>
              <div style={{fontFamily:P.mono,fontSize:28,fontWeight:700,color:P.orange}}>{cognitiveOverloadIndex}</div>
            </div>
          ) : null}
          <div style={{display:"inline-block",background:P.surface,borderRadius:12,padding:"12px 22px"}}>
            <div style={{fontSize:11,color:P.muted,marginBottom:4,textTransform:"uppercase",letterSpacing:1}}>Next session available in</div>
            <div style={{fontFamily:P.mono,fontSize:22,fontWeight:700,color:P.blue}}>{countdown}</div>
          </div>
        </Card>
      ) : null}

      <div style={{display:"flex",flexDirection:"column",gap:8,marginBottom:14}}>
        {modules.map(m=>(
          <div key={m.key} style={{background:P.card,border:`1px solid ${m.done?P.teal+"40":P.cardBorder}`,borderRadius:12,padding:"14px 16px",display:"flex",alignItems:"center",gap:14}}>
            <span style={{fontSize:26,width:36,textAlign:"center"}}>{m.icon}</span>
            <div style={{flex:1}}>
              <div style={{fontWeight:500,fontSize:14}}>{m.label}</div>
              <div style={{fontSize:12,color:P.muted}}>{m.time}</div>
            </div>
            {m.done
              ? <span style={{background:"rgba(104,211,145,0.15)",color:P.green,fontSize:12,padding:"4px 12px",borderRadius:20,fontWeight:500}}>✓ Completed</span>
              : sessionsBlocked
                ? <span style={{background:P.surface,color:P.muted,fontSize:12,padding:"4px 12px",borderRadius:20,border:`1px solid ${P.faint}`}}>Unavailable</span>
                : <Btn onClick={()=>onNavigate(m.key)} primary style={{fontSize:13,padding:"8px 16px"}}>Start →</Btn>}
          </div>
        ))}
      </div>

      {isWeeklyDay&&<Card style={{marginBottom:14,border:`1px solid rgba(167,139,250,0.3)`,background:"rgba(167,139,250,0.04)"}}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
          <div>
            <div style={{fontWeight:600,color:P.purple}}>📊 Weekly NASA-TLX Survey</div>
            <div style={{fontSize:12,color:P.muted,marginTop:2}}>Available Fridays · +25 NeuroCoins</div>
          </div>
          {hasNasaTLX
            ?<span style={{background:"rgba(104,211,145,0.15)",color:P.green,fontSize:12,padding:"4px 12px",borderRadius:20}}>✓ Done</span>
            :<Btn onClick={()=>onNavigate("nasatlx")} style={{background:`rgba(167,139,250,0.15)`,color:P.purple,border:`1px solid rgba(167,139,250,0.25)`,padding:"8px 16px",fontSize:13}}>Take Survey</Btn>}
        </div>
      </Card>}
    </div>
  );
}
