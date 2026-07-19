import { useState, useEffect, useRef } from 'react';
import { T } from '../../constants/tokens.js';
import { pickWords } from '../../constants/wordBank.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import LockedScreen from '../ui/LockedScreen.jsx';

export default function MemoryTest({onComplete,onBack,locked}) {
  const [phase,setPhase]=useState("intro");
  const [words]=useState(()=>pickWords(5));
  const [recall,setRecall]=useState("");
  const [studyT,setStudyT]=useState(12);
  const [distrT,setDistrT]=useState(20);
  const [recallStart,setRecallStart]=useState(null);
  const [distrScore,setDistrScore]=useState(0);
  const [mathQ,setMathQ]=useState({a:7,b:8});
  const [mathInput,setMathInput]=useState("");
  const studyRef=useRef(); const distrRef=useRef();

  useEffect(()=>{
    if(phase==="study"){
      studyRef.current=setInterval(()=>{setStudyT(t=>{if(t<=1){clearInterval(studyRef.current);setPhase("distract");newMath();return 0;}return t-1;});},1000);
      return()=>clearInterval(studyRef.current);
    }
    if(phase==="distract"){
      distrRef.current=setInterval(()=>{setDistrT(t=>{if(t<=1){clearInterval(distrRef.current);setPhase("recall");setRecallStart(Date.now());return 0;}return t-1;});},1000);
      return()=>clearInterval(distrRef.current);
    }
  },[phase]);

  const newMath=()=>{
    const ops=[["+","-","×"]]; const op=ops[0][Math.floor(Math.random()*3)];
    const a=Math.floor(Math.random()*12)+2; const b=Math.floor(Math.random()*12)+2;
    setMathQ({a,b,op,ans:op==="+"?a+b:op==="-"?a-b:a*b}); setMathInput("");
  };
  useEffect(()=>{if(phase==="distract")newMath();},[phase]);

  const checkMath=()=>{
    if(parseInt(mathInput)===mathQ.ans){setDistrScore(s=>s+1);newMath();}
    else setMathInput("");
  };

  const submitRecall=()=>{
    const rt=Date.now()-recallStart;
    const typed=recall.toUpperCase().split(/[\s,;.]+/).filter(w=>w.length>1);
    const correct=words.filter(w=>typed.includes(w)).length;
    onComplete({correct,total:5,accuracy:Math.round(correct/5*100),responseTime:rt,distractionScore:distrScore,wordSet:words,recalled:typed,timestamp:Date.now()});
  };

  if(locked) return <LockedScreen onBack={onBack} />;
  return (
    <Page title="Memory Test" onBack={onBack}>
      {phase==="intro"&&(
        <Card style={{maxWidth:400,margin:"0 auto",textAlign:"center"}} className="fade-in">
          <div style={{fontSize:48,marginBottom:12}}>🧩</div>
          <h2 style={{fontWeight:600,marginBottom:10}}>Working Memory Test</h2>
          <p style={{color:T.muted,fontSize:14,lineHeight:1.8,marginBottom:24}}>You'll see 5 words for 12 seconds. Memorize them! A short distraction task follows, then you'll need to recall the words.</p>
          <Btn onClick={()=>setPhase("study")} primary style={{padding:"13px 36px"}}>Begin</Btn>
        </Card>
      )}
      {phase==="study"&&(
        <Card style={{maxWidth:400,margin:"0 auto",textAlign:"center"}} className="fade-in">
          <div style={{fontSize:12,color:T.muted,fontFamily:T.mono,marginBottom:8}}>Memorize these words — {studyT}s remaining</div>
          <div style={{height:6,background:T.faint,borderRadius:4,marginBottom:24}}><div style={{background:T.teal,height:6,borderRadius:4,width:`${studyT/12*100}%`,transition:"width 1s linear"}} /></div>
          <div style={{display:"flex",flexWrap:"wrap",gap:12,justifyContent:"center",margin:"16px 0"}}>
            {words.map(w=><span key={w} style={{background:`rgba(45,212,191,0.1)`,border:`1px solid ${T.teal}40`,color:T.teal,padding:"12px 20px",borderRadius:10,fontWeight:700,fontSize:20,letterSpacing:2}}>{w}</span>)}
          </div>
        </Card>
      )}
      {phase==="distract"&&(
        <Card style={{maxWidth:360,margin:"0 auto",textAlign:"center"}} className="fade-in">
          <div style={{fontSize:12,color:T.muted,fontFamily:T.mono,marginBottom:4}}>Distraction task — {distrT}s</div>
          <div style={{height:4,background:T.faint,borderRadius:4,marginBottom:20}}><div style={{background:T.purple,height:4,borderRadius:4,width:`${distrT/20*100}%`,transition:"width 1s linear"}} /></div>
          <p style={{color:T.muted,fontSize:13,marginBottom:16}}>Solve quickly — don't think about the words!</p>
          <div style={{fontSize:44,fontWeight:700,fontFamily:T.mono,marginBottom:20,color:T.text}}>{mathQ.a} {mathQ.op} {mathQ.b} = ?</div>
          <input type="number" value={mathInput} onChange={e=>setMathInput(e.target.value)} onKeyDown={e=>e.key==="Enter"&&checkMath()} style={{textAlign:"center",fontSize:24,marginBottom:12}} placeholder="?" />
          <Btn onClick={checkMath} primary style={{width:"100%",padding:"11px"}}>Submit</Btn>
          <div style={{color:T.muted,fontSize:12,marginTop:10}}>Correct: {distrScore}</div>
        </Card>
      )}
      {phase==="recall"&&(
        <Card style={{maxWidth:400,margin:"0 auto"}} className="fade-in">
          <h2 style={{fontWeight:600,marginBottom:8}}>Recall the 5 words</h2>
          <p style={{color:T.muted,fontSize:14,marginBottom:16,lineHeight:1.7}}>Type the words you memorized — separated by spaces, commas, or one per line:</p>
          <textarea value={recall} onChange={e=>setRecall(e.target.value)} style={{height:100,resize:"none"}} placeholder="DOG  APPLE  HOUSE…" />
          <Btn onClick={submitRecall} primary style={{width:"100%",padding:"12px",marginTop:12}}>Submit Recall →</Btn>
        </Card>
      )}
    </Page>
  );
}
