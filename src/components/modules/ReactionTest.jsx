import { useState, useRef, useCallback } from 'react';
import { T } from '../../constants/tokens.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import LockedScreen from '../ui/LockedScreen.jsx';

export default function ReactionTest({onComplete,onBack,locked}) {
  const [phase,setPhase]=useState("intro");
  const [bkColor,setBkColor]=useState(T.bg);
  const [times,setTimes]=useState([]);
  const [round,setRound]=useState(0);
  const [missed,setMissed]=useState(0);
  const [tapStart,setTapStart]=useState(null);
  const timerRef=useRef();
  const ROUNDS=6;
  const STIMULI=["green","blue","yellow"];

  const startRound=useCallback(()=>{
    setBkColor(T.surface);
    const delay=1000+Math.random()*4000;
    timerRef.current=setTimeout(()=>{
      const stim=STIMULI[Math.floor(Math.random()*STIMULI.length)];
      const colors={green:"#68D391",blue:"#63B3ED",yellow:"#F6E05E"};
      setBkColor(colors[stim]);
      setPhase("tap");
      setTapStart(Date.now());
      timerRef.current=setTimeout(()=>{ setMissed(m=>m+1); advance(); }, 2500);
    },delay);
  },[]);

  const advance=useCallback(()=>{
    const r=round+1;
    setRound(r);
    if(r>=ROUNDS) setTimeout(finalize,400);
    else { setPhase("waiting"); setTimeout(startRound,800); }
  },[round,times]);

  const finalize=useCallback(()=>{
    const t=times; if(!t.length){onComplete({avg:0,median:0,sd:0,min:0,max:0,missed,timestamp:Date.now()});return;}
    const avg=Math.round(t.reduce((a,b)=>a+b)/t.length);
    const s=[...t].sort((a,b)=>a-b);
    const med=s[Math.floor(s.length/2)];
    const sd=Math.round(Math.sqrt(t.reduce((sum,v)=>sum+Math.pow(v-avg,2),0)/t.length));
    setPhase("results");
    setTimeout(()=>onComplete({avg,median:med,sd,min:Math.min(...t),max:Math.max(...t),missed,trials:ROUNDS,timestamp:Date.now()}),1500);
  },[times,missed]);

  const handleTap=()=>{
    if(phase==="waiting"){clearTimeout(timerRef.current);setMissed(m=>m+1);advance();return;}
    if(phase!=="tap")return;
    clearTimeout(timerRef.current);
    const rt=Date.now()-tapStart;
    setTimes(prev=>[...prev,rt]);
    advance();
  };

  if(locked) return <LockedScreen onBack={onBack} />;
  return (
    <Page title="Reaction Time" onBack={onBack}>
      {phase==="intro"&&(
        <Card style={{maxWidth:400,margin:"0 auto",textAlign:"center"}} className="fade-in">
          <div style={{fontSize:52,marginBottom:16}}>⚡</div>
          <h2 style={{fontWeight:600,marginBottom:10}}>Reaction Time Test</h2>
          <p style={{color:T.muted,fontSize:14,lineHeight:1.8,marginBottom:24}}>{ROUNDS} rounds. When the screen changes color — tap immediately! Don't tap early or you'll miss the round.</p>
          <Btn onClick={()=>{setRound(0);setTimes([]);setMissed(0);setPhase("waiting");startRound();}} primary style={{padding:"13px 36px",fontSize:15}}>Begin Test</Btn>
        </Card>
      )}
      {(phase==="waiting"||phase==="tap")&&(
        <div onClick={handleTap} style={{position:"fixed",inset:0,background:bkColor,display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",cursor:"pointer",userSelect:"none",transition:"background .1s"}}>
          <div style={{color:phase==="tap"?"#000":"rgba(255,255,255,0.6)",fontSize:56,fontWeight:700}}>{phase==="waiting"?"·  ·  ·":"TAP!"}</div>
          <div style={{color:phase==="tap"?"rgba(0,0,0,0.5)":"rgba(255,255,255,0.4)",fontSize:16,marginTop:16}}>{phase==="waiting"?"Wait for color change…":"Tap as fast as you can!"}</div>
          <div style={{color:"rgba(255,255,255,0.3)",fontSize:12,marginTop:40}}>Round {round+1}/{ROUNDS}</div>
          {times.length>0&&<div style={{color:"rgba(255,255,255,0.4)",fontSize:13,marginTop:8}}>Last: {times[times.length-1]}ms</div>}
        </div>
      )}
      {phase==="results"&&(
        <Card style={{maxWidth:380,margin:"0 auto",textAlign:"center"}} className="fade-in">
          <div style={{fontSize:40,marginBottom:12}}>✅</div>
          <h2 style={{fontWeight:600,color:T.teal}}>Complete!</h2>
          <p style={{color:T.muted,fontSize:14,marginTop:8}}>Saving biomarker data…</p>
          {times.length>0&&<div style={{fontFamily:T.mono,fontSize:20,color:T.teal,marginTop:16}}>{Math.round(times.reduce((a,b)=>a+b)/times.length)}ms avg</div>}
        </Card>
      )}
    </Page>
  );
}
