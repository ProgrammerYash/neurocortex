import { useState, useMemo } from 'react';
import { T } from '../../constants/tokens.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import LockedScreen from '../ui/LockedScreen.jsx';

export default function DailySurvey({onComplete,onBack,locked}) {
  const [data,setData]=useState({stress:5,fatigue:5,motivation:5,mood:5,sleep:7,study:3,homework:2,exam:false,socialStress:5,physicalActivity:0});
  const set=(k,v)=>setData(d=>({...d,[k]:v}));
  const questions=[
    {key:"stress",label:"Stress Level",desc:"1=very low, 10=very high",color:T.red},
    {key:"fatigue",label:"Fatigue",desc:"1=energetic, 10=exhausted",color:T.orange},
    {key:"motivation",label:"Motivation",desc:"1=very low, 10=very high",color:T.green},
    {key:"mood",label:"Mood",desc:"1=very poor, 10=excellent",color:T.blue},
    {key:"socialStress",label:"Social Stress",desc:"1=none, 10=very high",color:T.purple},
  ];
  const shuffled=useMemo(()=>[...questions].sort(()=>Math.random()-.5),[]);

  if(locked) return <LockedScreen onBack={onBack} />;
  return (
    <Page title="Daily Survey" onBack={onBack}>
      <Card style={{maxWidth:500,margin:"0 auto"}} className="fade-in">
        <h2 style={{fontWeight:600,marginBottom:20}}>Daily Wellbeing Survey</h2>
        {shuffled.map(q=>(
          <div key={q.key} style={{marginBottom:22}}>
            <div style={{display:"flex",justifyContent:"space-between",marginBottom:4}}>
              <label style={{fontSize:14,fontWeight:500,color:T.text}}>{q.label}</label>
              <span style={{fontWeight:700,color:q.color,fontSize:16,fontFamily:T.mono}}>{data[q.key]}</span>
            </div>
            <div style={{fontSize:11,color:T.muted,marginBottom:8}}>{q.desc}</div>
            <input type="range" min="1" max="10" step="1" value={data[q.key]} onChange={e=>set(q.key,+e.target.value)} style={{width:"100%",accentColor:q.color}} />
          </div>
        ))}
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:10,marginBottom:20}}>
          {[["sleep","Sleep (hrs)",0,12],["study","Study (hrs)",0,16],["homework","HW (hrs)",0,12]].map(([k,l,min,max])=>(
            <div key={k}>
              <label style={{fontSize:12,color:T.muted,display:"block",marginBottom:4}}>{l}</label>
              <input type="number" min={min} max={max} value={data[k]} onChange={e=>set(k,+e.target.value)} />
            </div>
          ))}
        </div>
        <div style={{marginBottom:20}}>
          <label style={{fontSize:13,color:T.muted,fontWeight:500}}>Major exam in the next 3 days?</label>
          <div style={{display:"flex",gap:10,marginTop:8}}>
            {[true,false].map(v=>(
              <button key={String(v)} onClick={()=>set("exam",v)} style={{flex:1,padding:"11px",borderRadius:8,border:`1px solid ${data.exam===v?T.teal:T.faint}`,background:data.exam===v?`rgba(45,212,191,0.1)`:T.surface,color:data.exam===v?T.teal:T.muted,fontWeight:data.exam===v?600:400,cursor:"pointer"}}>
                {v?"Yes":"No"}
              </button>
            ))}
          </div>
        </div>
        <Btn onClick={()=>onComplete({...data,timestamp:Date.now()})} primary style={{width:"100%",padding:"14px",fontSize:15}}>Submit Survey</Btn>
      </Card>
    </Page>
  );
}
