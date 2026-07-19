import { T } from '../../constants/tokens.js';
import { ACHIEVEMENTS_DEF } from '../../constants/gamification.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';

export default function AchievementsScreen({gameData,onBack}) {
  const g=gameData;
  if(!g) return <Page title="Achievements" onBack={onBack}><Card><p>Loading…</p></Card></Page>;
  return (
    <Page title="Achievements" onBack={onBack}>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}} className="fade-in">
        {ACHIEVEMENTS_DEF.map(a=>{
          const earned=g.achievements.includes(a.id);
          return (
            <Card key={a.id} style={{opacity:earned?1:0.45,border:`1px solid ${earned?T.gold+"50":T.faint}`,background:earned?`rgba(246,173,85,0.04)`:T.card}}>
              <div style={{fontSize:32,marginBottom:10}}>{earned?a.emoji:"🔒"}</div>
              <div style={{fontWeight:600,fontSize:14,color:earned?T.gold:T.muted,marginBottom:4}}>{a.name}</div>
              <div style={{fontSize:12,color:T.muted,lineHeight:1.6}}>{a.desc}</div>
            </Card>
          );
        })}
      </div>
    </Page>
  );
}
