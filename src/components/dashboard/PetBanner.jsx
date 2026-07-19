import { T } from '../../constants/tokens.js';
import { PET_TYPES } from '../../constants/gamification.js';
import { evolEmoji } from '../../utils/gamification.js';
import MiniBar from './MiniBar.jsx';

export default function PetBanner({g,onNavigate}) {
  const pet=g.pet;
  const p=PET_TYPES[pet.type]||PET_TYPES.fox;
  const nextLvlXp=(pet.level*pet.level)*50;
  return (
    <div onClick={()=>onNavigate("pet")} className="glow" style={{background:T.card,border:`1px solid ${T.cardBorder}`,borderRadius:14,padding:"14px 18px",marginBottom:14,cursor:"pointer",display:"flex",alignItems:"center",gap:16}}>
      <div className="heartbeat" style={{fontSize:44,width:56,height:56,background:`${p.color}15`,borderRadius:14,display:"flex",alignItems:"center",justifyContent:"center"}}>{p.emoji}</div>
      <div style={{flex:1}}>
        <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:6}}>
          <span style={{fontWeight:600,fontSize:15,color:p.color}}>{pet.name}</span>
          <span style={{fontSize:11,background:`${p.color}20`,color:p.color,padding:"2px 8px",borderRadius:20}}>Lv.{pet.level} {evolEmoji(pet.evolution)} {pet.evolution}</span>
        </div>
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:6}}>
          <MiniBar label="Happiness" val={pet.happiness} color={T.green} />
          <MiniBar label="Energy" val={pet.energy} color={T.teal} />
        </div>
        <div style={{marginTop:6}}>
          <MiniBar label={`XP to Lv.${pet.level+1}`} val={Math.min(100,Math.round(pet.xp/nextLvlXp*100))} color={p.color} />
        </div>
      </div>
    </div>
  );
}
