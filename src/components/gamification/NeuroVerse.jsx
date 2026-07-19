import { T } from '../../constants/tokens.js';
import { BRAIN_REGIONS } from '../../constants/gamification.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';

export default function NeuroVerse({gameData,sessions,onBack}) {
  const g=gameData;
  if(!g) return <Page title="NeuroVerse" onBack={onBack}><Card><p>Loading…</p></Card></Page>;
  const totalDays=g.totalDays;
  return (
    <Page title="NeuroVerse" onBack={onBack}>
      <Card style={{marginBottom:14,textAlign:"center",background:`radial-gradient(ellipse at 50% 0%, rgba(45,212,191,0.06), transparent 70%)`}}>
        <h2 style={{fontWeight:600,marginBottom:8}}>Your Neural Ecosystem</h2>
        <p style={{color:T.muted,fontSize:13,lineHeight:1.7}}>As you complete daily sessions, your digital brain grows new regions and neural pathways. Each study day unlocks new cognitive territory.</p>
        <div style={{fontSize:12,color:T.teal,marginTop:8}}>Study Days: {totalDays} · Regions Unlocked: {g.unlockedRegions.length}/{BRAIN_REGIONS.length}</div>
      </Card>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}}>
        {BRAIN_REGIONS.map((region,i)=>{
          const unlocked=g.unlockedRegions.includes(region.id);
          const progress=sessions.filter(s=>{
            if(region.id==="prefrontal") return !!s.attention;
            if(region.id==="hippocampus") return !!s.memory;
            if(region.id==="amygdala") return !!s.survey;
            if(region.id==="parietal") return !!s.reaction;
            if(region.id==="temporal") return !!s.typing;
            return !!s.survey;
          }).length;
          return (
            <Card key={region.id} style={{opacity:unlocked?1:0.35,border:`1px solid ${unlocked?region.color+"40":T.faint}`,background:unlocked?`${region.color}06`:T.card}}>
              <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:10}}>
                <div style={{width:36,height:36,borderRadius:10,background:unlocked?`${region.color}20`:T.surface,display:"flex",alignItems:"center",justifyContent:"center"}}>
                  {unlocked?<div style={{width:16,height:16,borderRadius:"50%",background:region.color}} />:<span style={{fontSize:16}}>🔒</span>}
                </div>
                <div>
                  <div style={{fontWeight:600,fontSize:13,color:unlocked?region.color:T.muted}}>{region.name}</div>
                  <div style={{fontSize:11,color:T.muted}}>{region.desc}</div>
                </div>
              </div>
              {unlocked&&<>
                <div style={{background:T.faint,borderRadius:4,height:4}}><div style={{background:region.color,height:4,borderRadius:4,width:`${Math.min(100,progress*3)}%`}} /></div>
                <div style={{fontSize:11,color:T.muted,marginTop:4}}>{progress} sessions recorded</div>
              </>}
              {!unlocked&&<div style={{fontSize:11,color:T.muted}}>Unlocks at day {(i+1)*10}</div>}
            </Card>
          );
        })}
      </div>
    </Page>
  );
}
