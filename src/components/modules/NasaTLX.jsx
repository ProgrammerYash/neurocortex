import { useState } from 'react';
import { T } from '../../constants/tokens.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';

export default function NasaTLX({onComplete,onBack}) {
  const [data,setData]=useState({mentalDemand:50,physicalDemand:30,temporalDemand:50,performance:50,effort:50,frustration:40});
  const dims=[
    {key:"mentalDemand",label:"Mental Demand",desc:"How mentally demanding was the task?",color:T.blue},
    {key:"physicalDemand",label:"Physical Demand",desc:"How physically demanding was it?",color:T.green},
    {key:"temporalDemand",label:"Temporal Demand",desc:"How hurried or rushed was the pace?",color:T.orange},
    {key:"performance",label:"Performance",desc:"How successful were you? (higher=better)",color:T.teal},
    {key:"effort",label:"Effort",desc:"How hard did you work to accomplish the task?",color:T.purple},
    {key:"frustration",label:"Frustration",desc:"How insecure, discouraged, irritated?",color:T.red},
  ];
  const tlxScore=Math.round(Object.values(data).reduce((a,b)=>a+b)/6);
  return (
    <Page title="NASA-TLX Weekly Survey" onBack={onBack}>
      <Card style={{maxWidth:500,margin:"0 auto"}} className="fade-in">
        <div style={{background:`rgba(167,139,250,0.08)`,border:`1px solid rgba(167,139,250,0.2)`,borderRadius:10,padding:"12px 16px",marginBottom:20}}>
          <div style={{fontWeight:600,color:T.purple,marginBottom:4}}>NASA Task Load Index</div>
          <p style={{fontSize:12,color:T.muted,lineHeight:1.7}}>Rate your cognitive workload over the past week. This validated research scale helps track daily wellness patterns.</p>
        </div>
        {dims.map(d=>(
          <div key={d.key} style={{marginBottom:20}}>
            <div style={{display:"flex",justifyContent:"space-between",marginBottom:4}}>
              <label style={{fontSize:14,fontWeight:600,color:T.text}}>{d.label}</label>
              <span style={{fontFamily:T.mono,fontWeight:700,color:d.color}}>{data[d.key]}</span>
            </div>
            <div style={{fontSize:11,color:T.muted,marginBottom:8}}>{d.desc}</div>
            <div style={{display:"flex",alignItems:"center",gap:10}}>
              <span style={{fontSize:10,color:T.muted,minWidth:24,textAlign:"center"}}>Low</span>
              <input type="range" min="0" max="100" step="5" value={data[d.key]} onChange={e=>setData(prev=>({...prev,[d.key]:+e.target.value}))} style={{flex:1,accentColor:d.color}} />
              <span style={{fontSize:10,color:T.muted,minWidth:28,textAlign:"center"}}>High</span>
            </div>
          </div>
        ))}
        <div style={{background:T.surface,borderRadius:10,padding:"14px",marginBottom:20,textAlign:"center"}}>
          <div style={{fontSize:12,color:T.muted,marginBottom:4}}>Overall NASA-TLX Score</div>
          <div style={{fontSize:36,fontWeight:700,color:tlxScore>65?T.red:tlxScore>40?T.orange:T.green}}>{tlxScore}</div>
          <div style={{fontSize:12,color:T.muted}}>{tlxScore>65?"High workload":tlxScore>40?"Moderate workload":"Low workload"}</div>
        </div>
        <Btn onClick={()=>onComplete({...data,tlxScore,timestamp:Date.now()})} primary style={{width:"100%",padding:"14px"}}>Submit NASA-TLX +25🪙</Btn>
      </Card>
    </Page>
  );
}
