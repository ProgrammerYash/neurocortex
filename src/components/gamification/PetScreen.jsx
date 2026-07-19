import { useState } from 'react';
import { T } from '../../constants/tokens.js';
import { PET_TYPES, HOUSE_ITEMS } from '../../constants/gamification.js';
import { evolEmoji } from '../../utils/gamification.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';

export default function PetScreen({gameData,updateGame,onBack,showToast}) {
  const [tab,setTab]=useState("home");
  const g=gameData;
  if(!g) return <Page title="Pet" onBack={onBack}><Card><p>Loading…</p></Card></Page>;
  const pet=g.pet; const p=PET_TYPES[pet.type]||PET_TYPES.fox;

  const buyItem=async (item)=>{
    if(g.coins<item.cost){showToast("Not enough NeuroCoins! Complete more sessions.","error");return;}
    if(g.house.items.includes(item.id)){showToast("Already owned!","error");return;}
    await updateGame(prev=>({...prev,coins:prev.coins-item.cost,house:{...prev.house,items:[...prev.house.items,item.id]}}));
    showToast(`${item.emoji} ${item.name} added to your home!`,"success");
  };

  return (
    <Page title={`${p.name}'s Home`} onBack={onBack}>
      {/* Pet display */}
      <Card style={{textAlign:"center",marginBottom:14,background:`linear-gradient(135deg,rgba(45,212,191,0.04),rgba(99,179,237,0.04))`}}>
        <div className="heartbeat" style={{fontSize:80,marginBottom:12}}>{p.emoji}</div>
        <div style={{fontWeight:700,fontSize:22,color:p.color}}>{pet.name}</div>
        <div style={{color:T.muted,fontSize:13,marginTop:4}}>{evolEmoji(pet.evolution)} {pet.evolution.charAt(0).toUpperCase()+pet.evolution.slice(1)} · Level {pet.level}</div>
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:10,marginTop:20}}>
          {[["Happiness",pet.happiness,T.green,"😊"],["Energy",pet.energy,T.teal,"⚡"],["XP",Math.min(100,Math.round(pet.xp/(pet.level*pet.level*50)*100)),p.color,"🌟"]].map(([l,v,c,e])=>(
            <div key={l} style={{background:T.surface,borderRadius:10,padding:"10px 8px"}}>
              <div style={{fontSize:18,marginBottom:4}}>{e}</div>
              <div style={{fontSize:11,color:T.muted,marginBottom:6}}>{l}</div>
              <div style={{background:T.faint,borderRadius:4,height:6}}><div style={{background:c,height:6,borderRadius:4,width:`${v}%`,transition:"width .6s"}} /></div>
            </div>
          ))}
        </div>
        {pet.evolution!=="legendary"&&<p style={{fontSize:12,color:T.muted,marginTop:14}}>Complete daily sessions to gain XP and evolve your companion!</p>}
        {pet.evolution==="legendary"&&<p style={{fontSize:13,color:T.gold,marginTop:14}}>✨ Your companion has reached Legendary status!</p>}
      </Card>

      {/* Pet house */}
      <div style={{display:"flex",gap:4,background:T.surface,padding:4,borderRadius:10,marginBottom:14}}>
        {["home","shop"].map(t=>(
          <button key={t} onClick={()=>setTab(t)} style={{flex:1,padding:"9px",border:"none",borderRadius:7,fontWeight:500,fontSize:13,cursor:"pointer",background:tab===t?T.card:T.surface,color:tab===t?T.teal:T.muted,textTransform:"capitalize"}}>
            {t==="home"?"🏠 Pet Home":"🛒 Shop"}
          </button>
        ))}
      </div>

      {tab==="home"&&(
        <Card>
          <SectionTitle>Your Study Space</SectionTitle>
          <div style={{minHeight:180,background:T.surface,borderRadius:12,padding:20,marginBottom:14,display:"flex",flexWrap:"wrap",gap:16,alignItems:"center",justifyContent:"center"}}>
            {g.house.items.length===0?(
              <p style={{color:T.muted,fontSize:13}}>Your space is empty. Visit the shop to decorate!</p>
            ):g.house.items.map(id=>{
              const item=HOUSE_ITEMS.find(i=>i.id===id);
              return item?<span key={id} style={{fontSize:36}} title={item.name}>{item.emoji}</span>:null;
            })}
            <span style={{fontSize:50}}>{p.emoji}</span>
          </div>
          <div style={{display:"flex",gap:6,alignItems:"center",fontSize:13,color:T.muted}}>
            <span>🪙</span><span>{g.coins} NeuroCoins available</span>
          </div>
        </Card>
      )}

      {tab==="shop"&&(
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}}>
          {HOUSE_ITEMS.map(item=>{
            const owned=g.house.items.includes(item.id);
            return (
              <Card key={item.id} style={{textAlign:"center",opacity:owned?0.7:1}}>
                <div style={{fontSize:36,marginBottom:8}}>{item.emoji}</div>
                <div style={{fontWeight:500,fontSize:14,marginBottom:4}}>{item.name}</div>
                <div style={{color:T.gold,fontSize:13,marginBottom:12}}>🪙 {item.cost}</div>
                <Btn onClick={()=>buyItem(item)} style={{width:"100%",padding:"8px",fontSize:12,background:owned?"transparent":T.surface,color:owned?T.green:T.text,border:`1px solid ${owned?T.green:T.faint}`}} disabled={owned}>{owned?"✓ Owned":"Buy"}</Btn>
              </Card>
            );
          })}
        </div>
      )}
    </Page>
  );
}
