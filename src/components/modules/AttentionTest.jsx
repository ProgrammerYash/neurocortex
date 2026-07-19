import { useState } from 'react';
import { T } from '../../constants/tokens.js';
import { STROOP_COLORS, genStroop } from '../../constants/stroop.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import LockedScreen from '../ui/LockedScreen.jsx';

export default function AttentionTest({onComplete,onBack,locked}) {
  const [phase,setPhase]=useState("intro");
  const [items]=useState(()=>genStroop(12));
  const [idx,setIdx]=useState(0);
  const [correct,setCorrect]=useState(0);
  const [errors,setErrors]=useState(0);
  const [rts,setRts]=useState([]);
  const [itemT,setItemT]=useState(null);
  const [startT,setStartT]=useState(null);

  const begin=()=>{ setPhase("test"); setStartT(Date.now()); setItemT(Date.now()); };

  const answer=(choice)=>{
    const rt=Date.now()-itemT;
    const isCorrect=choice===items[idx].inkName;
    const newCorrect=correct+(isCorrect?1:0);
    const newErrors=errors+(isCorrect?0:1);
    const newRts=[...rts,rt];
    const next=idx+1;
    if(next>=items.length){
      const total=Date.now()-startT;
      onComplete({accuracy:Math.round(newCorrect/items.length*100),completionTime:total,errors:newErrors,avgRT:Math.round(newRts.reduce((a,b)=>a+b)/newRts.length),congruentAcc:Math.round(items.filter((it,i)=>it.congruent&&(i<idx||(i===idx&&isCorrect))).length/items.filter(it=>it.congruent).length*100),incongruentAcc:Math.round(items.filter((it,i)=>!it.congruent&&(i<idx||(i===idx&&isCorrect))).length/Math.max(1,items.filter(it=>!it.congruent).length)*100),timestamp:Date.now()});
      return;
    }
    setCorrect(newCorrect); setErrors(newErrors); setRts(newRts);
    setIdx(next); setItemT(Date.now());
  };

  const item=items[idx]||items[0];
  if(locked) return <LockedScreen onBack={onBack} />;
  return (
    <Page title="Attention Test" onBack={onBack}>
      {phase==="intro"&&(
        <Card style={{maxWidth:400,margin:"0 auto",textAlign:"center"}} className="fade-in">
          <div style={{fontSize:48,marginBottom:12}}>🎯</div>
          <h2 style={{fontWeight:600,marginBottom:10}}>Stroop Attention Test</h2>
          <p style={{color:T.muted,fontSize:14,lineHeight:1.8,marginBottom:16}}>Tap the <strong style={{color:T.teal}}>COLOR OF THE INK</strong> — not what the word says. Work quickly and accurately!</p>
          <div style={{fontSize:40,fontWeight:800,color:"#63B3ED",margin:"20px 0",letterSpacing:3}}>RED</div>
          <p style={{fontSize:13,color:T.muted,marginBottom:20}}>↑ Answer: BLUE (the ink color)</p>
          <Btn onClick={begin} primary style={{padding:"13px 36px"}}>Start Test</Btn>
        </Card>
      )}
      {phase==="test"&&idx<items.length&&(
        <Card style={{maxWidth:380,margin:"0 auto",textAlign:"center"}} className="fade-in">
          <div style={{display:"flex",justifyContent:"space-between",marginBottom:20,fontSize:13,color:T.muted}}>
            <span>{idx+1}/{items.length}</span>
            <span>✓{correct} ✗{errors}</span>
          </div>
          <div style={{fontSize:60,fontWeight:800,color:item.inkColor,marginBottom:32,letterSpacing:4,lineHeight:1}}>{item.word}</div>
          <p style={{fontSize:13,color:T.muted,marginBottom:16}}>What color is the INK?</p>
          <div style={{display:"flex",gap:10,justifyContent:"center",flexWrap:"wrap"}}>
            {STROOP_COLORS.map(c=>(
              <button key={c.name} onClick={()=>answer(c.name)} style={{background:c.hex,color:"#000",padding:"12px 18px",borderRadius:10,fontWeight:700,fontSize:14,border:"none",cursor:"pointer",minWidth:80}}>{c.name}</button>
            ))}
          </div>
        </Card>
      )}
    </Page>
  );
}
