import { useState, useEffect, useRef, useCallback } from 'react';
import { T } from '../../constants/tokens.js';
import { TYPING_PASSAGES } from '../../constants/typingPassages.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import LockedScreen from '../ui/LockedScreen.jsx';

export default function TypingTest({onComplete,onBack,locked}) {
  const [phase,setPhase]=useState("intro");
  const [passage]=useState(()=>TYPING_PASSAGES[Math.floor(Math.random()*TYPING_PASSAGES.length)]);
  const [typed,setTyped]=useState("");
  const [time,setTime]=useState(30);
  const [keyData,setKeyData]=useState([]);
  const [backspaces,setBackspaces]=useState(0);
  const [lastKeyT,setLastKeyT]=useState(null);
  const [intervals,setIntervals]=useState([]);
  const [dwells,setDwells]=useState([]);
  const timerRef=useRef();
  const inputRef=useRef();

  useEffect(()=>{
    if(phase!=="test")return;
    timerRef.current=setInterval(()=>{
      setTime(t=>{if(t<=1){clearInterval(timerRef.current);finalize();return 0;}return t-1;});
    },1000);
    return()=>clearInterval(timerRef.current);
  },[phase]);

  const finalize=useCallback(()=>{
    const words=typed.trim().split(/\s+/).filter(w=>w.length>0);
    const wpm=words.length*2;
    const targetWords=passage.split(" ");
    let errors=0;
    words.forEach((w,i)=>{if(w.toLowerCase()!==targetWords[i]?.toLowerCase())errors++;});
    const errRate=words.length>0?Math.round(errors/words.length*100):0;
    const avgInterval=intervals.length>0?Math.round(intervals.reduce((a,b)=>a+b)/intervals.length):0;
    const variance=intervals.length>1?Math.round(intervals.reduce((s,v)=>s+Math.pow(v-avgInterval,2),0)/intervals.length):0;
    const avgDwell=dwells.length>0?Math.round(dwells.reduce((a,b)=>a+b)/dwells.length):0;
    const bursts=typed.split(/\s{2,}/).filter(s=>s.length>3).length;
    const pauseFreq=intervals.filter(i=>i>500).length;
    setPhase("results");
    setTimeout(()=>onComplete({wpm,errorRate:errRate,backspaces,avgInterval,variance,avgDwell,burstLength:bursts,pauseFrequency:pauseFreq,totalKeys:keyData.length,errCorrectionRate:backspaces>0?Math.round(backspaces/keyData.length*100):0,timestamp:Date.now()}),1500);
  },[typed,passage,intervals,dwells,backspaces,keyData]);

  const handleKeyDown=useCallback((e)=>{
    const now=Date.now();
    if(e.key==="Backspace")setBackspaces(b=>b+1);
    setKeyData(k=>[...k,{key:e.key,down:now}]);
    if(lastKeyT&&now-lastKeyT<2000)setIntervals(iv=>[...iv,now-lastKeyT]);
    setLastKeyT(now);
  },[lastKeyT]);

  const handleKeyUp=useCallback((e)=>{
    const now=Date.now();
    setKeyData(prev=>{
      const last=[...prev];
      const idx=last.findLastIndex(k=>k.key===e.key&&!k.up);
      if(idx>=0){const dwell=now-last[idx].down;setDwells(d=>[...d,dwell]);last[idx]={...last[idx],up:now,dwell};}
      return last;
    });
  },[]);

  if(locked) return <LockedScreen onBack={onBack} />;
  return (
    <Page title="Typing Biomarkers" onBack={onBack}>
      {phase==="intro"&&(
        <Card style={{maxWidth:500,margin:"0 auto"}} className="fade-in">
          <div style={{fontSize:40,marginBottom:12,textAlign:"center"}}>⌨️</div>
          <h2 style={{fontWeight:600,textAlign:"center",marginBottom:10}}>Typing Analysis</h2>
          <p style={{color:T.muted,fontSize:14,lineHeight:1.8,marginBottom:16}}>Type the passage below for 30 seconds. Your keystroke timing, rhythm, and error patterns are analyzed as behavioral biomarkers.</p>
          <div style={{background:T.surface,border:`1px solid ${T.faint}`,borderRadius:10,padding:"14px",fontSize:14,lineHeight:1.9,color:T.muted,fontStyle:"italic",marginBottom:20}}>{passage}</div>
          <Btn onClick={()=>{setPhase("test");setTimeout(()=>inputRef.current?.focus(),100);}} primary style={{width:"100%",padding:"13px"}}>Start 30-Second Test</Btn>
        </Card>
      )}
      {phase==="test"&&(
        <Card style={{maxWidth:500,margin:"0 auto"}} className="fade-in">
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:14}}>
            <span style={{fontWeight:600}}>Type the passage:</span>
            <span style={{fontFamily:T.mono,fontSize:24,fontWeight:700,color:time<=5?T.red:T.teal}}>{time}s</span>
          </div>
          <div style={{background:T.surface,borderRadius:8,padding:"12px",fontSize:13,lineHeight:1.8,color:T.muted,marginBottom:12,fontStyle:"italic"}}>{passage}</div>
          <textarea ref={inputRef} value={typed} onChange={e=>setTyped(e.target.value)} onKeyDown={handleKeyDown} onKeyUp={handleKeyUp}
            style={{width:"100%",height:110,resize:"none",border:`2px solid ${T.teal}`,borderRadius:8,padding:"10px",fontSize:14,lineHeight:1.7}} placeholder="Start typing here…" />
          <div style={{display:"flex",gap:16,marginTop:10,fontSize:12,color:T.muted}}>
            <span>Words: {typed.trim().split(/\s+/).filter(w=>w).length}</span>
            <span>Keys: {keyData.length}</span>
            <span>Backspaces: {backspaces}</span>
          </div>
        </Card>
      )}
      {phase==="results"&&(
        <Card style={{maxWidth:380,margin:"0 auto",textAlign:"center"}} className="fade-in">
          <div style={{fontSize:40,marginBottom:12}}>✅</div>
          <h2 style={{fontWeight:600,color:T.teal}}>Typing Data Captured!</h2>
          <p style={{color:T.muted,fontSize:14,marginTop:8}}>Analyzing keystroke biomarkers…</p>
        </Card>
      )}
    </Page>
  );
}
