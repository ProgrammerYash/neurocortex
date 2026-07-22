import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { T } from '../../constants/tokens.js';
import Btn from '../ui/Btn.jsx';
import { fetchUnreadMessageCount } from '../../store/messages.js';
import { studyFrequencyLabel } from '../../constants/studyFrequency.js';
import { ROUTES } from '../../routing/routePaths.js';
import PetBanner from './PetBanner.jsx';
import TodayTab from './TodayTab.jsx';
import ProgressTab from './ProgressTab.jsx';
import ConsentStatusTab from './ConsentStatusTab.jsx';
import { fetchMyConsentStatus } from '../../store/consent.js';
import { calcBurnout } from '../../utils/burnout.js';

export default function Dashboard({user,sessions,todaySessions,todayComplete,gameData,countdown,onNavigate,onLogout,showToast,unreadCount=0,onUnreadChange}) {
  const navigate = useNavigate();
  const [tab,setTab]=useState("today");
  const [sessionBlockMessage,setSessionBlockMessage]=useState(null);
  const [localUnread, setLocalUnread] = useState(unreadCount);
  const g=gameData;
  const isWeeklyDay=new Date().getDay()===5; // Friday
  const hasNasaTLX=!!todaySessions?.nasaTLX;
  const modules=[
    {key:"reaction",  label:"Reaction Time",      icon:"⚡",time:"~1 min", done:!!todaySessions.reaction},
    {key:"typing",    label:"Typing Biomarkers",   icon:"⌨️",time:"3 rounds",done:!!todaySessions.typing},
    {key:"memory",    label:"Memory Test",          icon:"🧩",time:"~1 min",done:!!todaySessions.memory},
    {key:"attention", label:"Attention / Stroop",   icon:"🎯",time:"~45 sec",done:!!todaySessions.attention},
    {key:"survey",    label:"Daily Survey",         icon:"📋",time:"~1 min", done:!!todaySessions.survey},
  ];
  const completed=modules.filter(m=>m.done).length;
  const pct=Math.round(completed/modules.length*100);
  const cognitiveOverloadIndex = todayComplete ? calcBurnout(todaySessions) : null;

  useEffect(() => {
    let active = true;
    fetchUnreadMessageCount()
      .then(data => {
        if (!active) return;
        const count = Number(data.unread_count) || 0;
        setLocalUnread(count);
        onUnreadChange?.(count);
      })
      .catch(() => {});
    return () => { active = false; };
  }, [user?.id, onUnreadChange]);

  useEffect(() => {
    setLocalUnread(unreadCount);
  }, [unreadCount]);

  useEffect(() => {
    let active = true;
    fetchMyConsentStatus()
      .then(status => {
        if (!active) return;
        setSessionBlockMessage(status.session_eligible ? null : (status.session_block_message || null));
      })
      .catch(() => {
        if (active) setSessionBlockMessage(null);
      });
    return () => { active = false; };
  }, [user?.id, sessions.length]);

  return (
    <div style={{maxWidth:720,margin:"0 auto",padding:"1rem 1rem 4rem"}}>
      {/* Header */}
      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",padding:"1rem 0 1.5rem"}}>
        <div>
          <div style={{display:"flex",alignItems:"center",gap:10}}>
            <span style={{fontSize:22}}>🧠</span>
            <span style={{fontWeight:700,fontSize:18,background:`linear-gradient(135deg,${T.teal},${T.blue})`,WebkitBackgroundClip:"text",WebkitTextFillColor:"transparent"}}>NeuroCortex</span>
          </div>
          <div style={{fontFamily:T.mono,fontSize:11,color:T.muted,marginTop:2}}>{user?.id}</div>
        </div>
        <div style={{display:"flex",gap:8,alignItems:"center",flexWrap:'wrap',justifyContent:'flex-end'}}>
          <Btn onClick={() => navigate(ROUTES.participantSettings)} style={{fontSize:12,padding:"7px 12px"}} aria-label="Participant settings">
            ⚙ Settings
          </Btn>
          <Btn onClick={() => onNavigate('inbox')} style={{fontSize:12,padding:"7px 12px", position:'relative'}}>
            Inbox
            {localUnread > 0 && (
              <span style={{
                position:'absolute',
                top:-6,
                right:-6,
                minWidth:18,
                height:18,
                borderRadius:999,
                background:T.red,
                color:'#fff',
                fontSize:10,
                fontWeight:700,
                display:'inline-flex',
                alignItems:'center',
                justifyContent:'center',
                padding:'0 4px',
              }}>
                {localUnread}
              </span>
            )}
          </Btn>
          {g&&<div style={{display:"flex",alignItems:"center",gap:6,background:T.surface,borderRadius:20,padding:"6px 12px",border:`1px solid ${T.faint}`}}>
            <span style={{fontSize:14}}>🪙</span>
            <span style={{fontSize:13,fontWeight:600,color:T.gold}}>{g.coins}</span>
          </div>}
          <Btn onClick={onLogout} style={{fontSize:12,padding:"7px 12px"}}>Sign Out</Btn>
        </div>
      </div>

      {/* Pet banner */}
      {g&&<PetBanner g={g} onNavigate={onNavigate} />}

      {/* Stats row */}
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:8,marginBottom:16}}>
        {[
          {label:"Streak",    val:`${g?.streak||0}🔥`,sub:"days"},
          {label:"Study Days",val:g?.totalDays||0,  sub:"total"},
          {label:"Pet Level", val:`Lv.${g?.pet?.level||1}`,sub:g?.pet?.evolution||"baby"},
          {label:"Week %",    val:sessions.length>=7?Math.round(sessions.slice(-7).length/7*100)+"%":"—",sub:"completion"},
        ].map(s=>(
          <div key={s.label} style={{background:T.card,border:`1px solid ${T.cardBorder}`,borderRadius:10,padding:"12px 10px",textAlign:"center"}}>
            <div style={{fontSize:11,color:T.muted,marginBottom:4}}>{s.label}</div>
            <div style={{fontSize:20,fontWeight:700,color:T.teal}}>{s.val}</div>
            <div style={{fontSize:11,color:T.muted}}>{s.sub}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div style={{display:"flex",gap:4,background:T.surface,padding:4,borderRadius:10,marginBottom:16}}>
        {["today","progress","study","neuroverse"].map(t=>(
          <button key={t} onClick={()=>setTab(t)} style={{flex:1,padding:"9px",border:"none",borderRadius:7,fontWeight:500,fontSize:13,cursor:"pointer",background:tab===t?T.card:T.surface,color:tab===t?T.teal:T.muted,transition:"all .2s",textTransform:"capitalize"}}>
            {t==="neuroverse"?"NeuroVerse":t==="today"?"Today":t==="study"?"Enrollment":"Progress"}
          </button>
        ))}
      </div>

      {tab==="today"&&<TodayTab modules={modules} completed={completed} pct={pct} todayComplete={todayComplete} countdown={countdown} isWeeklyDay={isWeeklyDay} hasNasaTLX={hasNasaTLX} onNavigate={onNavigate} sessionBlockMessage={sessionBlockMessage} cognitiveOverloadIndex={cognitiveOverloadIndex} studyScheduleLabel={studyFrequencyLabel(user?.studyFrequency)} />}
      {tab==="progress"&&<ProgressTab sessions={sessions} />}
      {tab==="study"&&<ConsentStatusTab showToast={showToast} />}
      {tab==="neuroverse"&&<div style={{textAlign:"center",padding:"2rem"}}><Btn onClick={()=>onNavigate("neuroverse")} primary style={{padding:"14px 32px"}}>Open NeuroVerse 🌐</Btn><br/><Btn onClick={()=>onNavigate("pet")} style={{marginTop:12,padding:"12px 28px"}}>Pet Home 🏠</Btn><br/><Btn onClick={()=>onNavigate("achievements")} style={{marginTop:12,padding:"12px 28px"}}>Achievements 🏆</Btn></div>}

      {/* Bottom nav */}
      <div style={{position:"fixed",bottom:0,left:0,right:0,background:T.surface,borderTop:`1px solid ${T.faint}`,display:"flex",justifyContent:"space-around",padding:"10px 0 12px",zIndex:100}}>
        {[["🏠","Home","dashboard"],["🧠","NeuroVerse","neuroverse"],["🐾","My Pet","pet"],["🏆","Awards","achievements"]].map(([e,l,s])=>(
          <button key={s} onClick={()=>onNavigate(s)} style={{background:"none",border:"none",color:T.muted,fontSize:11,display:"flex",flexDirection:"column",alignItems:"center",gap:3,padding:"4px 16px",cursor:"pointer"}}>
            <span style={{fontSize:20}}>{e}</span>{l}
          </button>
        ))}
      </div>
    </div>
  );
}
