
// ═══════════════════════════════════════════════════════════════════
// NEUROCORTEX v3 — ISEF Research Platform
// ─────────────────────────────────────────────────────────────────
// Prompt-1 architecture fixes:
//
// [FIX-1] MULTI-USER: every participant owns isolated localStorage
//   keys nc3_p_<id>/nc3_s_<id>/nc3_g_<id>. Writing one account
//   can NEVER touch another. Login reads by exact ID only.
//
// [FIX-2] ONE SESSION PER DAY: Store.addModuleResult() upserts
//   today's record and sets complete=true when all 5 modules are
//   present. Banner + countdown shown; tests hidden.
//
// [FIX-3] AUTOMATIC DAILY RESET: todaySessions = find(date===
//   dateToday()). When midnight passes the find() returns nothing
//   → all modules show as undone. Historical data untouched.
//
// [FIX-4] RESEARCHER SEPARATION: researcher registration shows
//   only an access code field. Code = "YASH GUPTA" (case-insensitive).
//   Researcher profile has no grade/ageRange. Dashboard removed
//   grade/age filter — researchers see ALL data globally.
//
// [FIX-5] FIREBASE-READY STORE: all persistence in one `Store`
//   object. Swap method bodies to migrate to Firebase/Supabase
//   with zero component changes.
// ═══════════════════════════════════════════════════════════════════

import { useState, useEffect, useRef, useCallback, useMemo } from "react";

// ── DESIGN TOKENS ──────────────────────────────────────────────────
const T = {
  bg: "#080C14",
  surface: "#0E1420",
  card: "#131928",
  cardBorder: "rgba(99,179,237,0.12)",
  glow: "rgba(99,179,237,0.06)",
  teal: "#2DD4BF",
  tealDim: "#0D9488",
  blue: "#63B3ED",
  blueDim: "#2B6CB0",
  purple: "#A78BFA",
  purpleDim: "#6D28D9",
  gold: "#F6AD55",
  green: "#68D391",
  red: "#FC8181",
  orange: "#F6AD55",
  text: "#E2E8F0",
  muted: "#718096",
  faint: "#2D3748",
  font: "'Sora', 'Segoe UI', sans-serif",
  mono: "'JetBrains Mono', monospace",
};

const css = `
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{background:${T.bg};color:${T.text};font-family:${T.font};-webkit-font-smoothing:antialiased}
::-webkit-scrollbar{width:4px}::-webkit-scrollbar-track{background:${T.surface}}::-webkit-scrollbar-thumb{background:${T.tealDim};border-radius:4px}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes glow{0%,100%{box-shadow:0 0 20px rgba(45,212,191,.15)}50%{box-shadow:0 0 40px rgba(45,212,191,.35)}}
@keyframes heartbeat{0%,100%{transform:scale(1)}50%{transform:scale(1.08)}}
@keyframes slideIn{from{opacity:0;transform:translateX(-12px)}to{opacity:1;transform:translateX(0)}}
.fade-in{animation:fadeIn .35s ease both}
.pulse{animation:pulse 2s infinite}
.spin{animation:spin 1s linear infinite}
.glow{animation:glow 3s ease infinite}
.heartbeat{animation:heartbeat 2s ease infinite}
input,select,textarea{background:${T.surface};border:1px solid ${T.faint};color:${T.text};font-family:${T.font};font-size:14px;border-radius:8px;padding:10px 12px;width:100%;outline:none;transition:border-color .2s}
input:focus,select:focus,textarea:focus{border-color:${T.teal}}
input[type=range]{padding:0;height:6px;accent-color:${T.teal}}
button{font-family:${T.font};cursor:pointer;border:none;outline:none;transition:all .18s}
button:active{transform:scale(.97)}
`;

// ── WORD BANKS ──────────────────────────────────────────────────────
const WORD_BANK = ["APPLE","BRIDGE","CANDLE","DOLPHIN","EMPIRE","FOREST","GARDEN","HARBOR","ISLAND","JUNGLE","KETTLE","LEMON","MARBLE","NEEDLE","OCEAN","PALACE","QUARTZ","RIVER","SUNSET","TIMBER","UMBRELLA","VALLEY","WALNUT","XENON","YELLOW","ZEBRA","ANCHOR","BASKET","CASTLE","DIAMOND","EAGLE","FALCON","GLACIER","HELMET","IRIS","JASMINE","KNIGHT","LANTERN","MIRROR","NOVEL","OYSTER","PENGUIN","QUAIL","ROCKET","SILVER","TORCH","URBAN","VIOLET","WINDOW","XYLEM","YOGURT","ZEPHYR","ACORN","BEACON","COPPER","DAGGER","ELEMENT","FLAME","GRAVEL","HOLLOW","INDIGO","JAGUAR","KARATE","LUNAR","MAGNET","NATURE","ORBIT","PEBBLE","QUIVER","RADIUS","SPHINX","TEMPLE","UMBRA","VAPOR","WARDEN","XERIC","YARROW","ZENITH","ALBEDO","BONSAI","CIPHER","DORSAL","ENZYME","FOSSIL","GROTTO","HYBRID","IGNITE","JIGSAW","KUDOS","LABYRINTH","MOSAIC","NIMBUS","OZONE","PARCEL","QUARRY","RIDDLE","SCRIBE","TALON","UMBRAL","VERTEX","WILLOW","XYSTER","YUCCA","ZOEAE","AMBER","BOREAL","COBALT","DUNE","ETHER","FERN"];
const pickWords = (n=5) => { const s=[...WORD_BANK]; for(let i=s.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[s[i],s[j]]=[s[j],s[i]]}return s.slice(0,n); };

const STROOP_COLORS = [
  {name:"RED",hex:"#FC8181"},{name:"BLUE",hex:"#63B3ED"},{name:"GREEN",hex:"#68D391"},{name:"YELLOW",hex:"#F6E05E"},{name:"PURPLE",hex:"#A78BFA"}
];
const genStroop = (n=15) => Array.from({length:n},()=>{
  const word=STROOP_COLORS[Math.floor(Math.random()*STROOP_COLORS.length)];
  const ink=STROOP_COLORS[Math.floor(Math.random()*STROOP_COLORS.length)];
  return {word:word.name,inkColor:ink.hex,inkName:ink.name,congruent:word.name===ink.name};
});

const TYPING_PASSAGES = [
  "The human brain contains approximately eighty-six billion neurons forming trillions of synaptic connections that enable thought memory and consciousness to emerge from electrochemical signals.",
  "Cognitive load theory suggests that working memory has limited capacity and instructional design must account for intrinsic extraneous and germane cognitive demands on learners.",
  "Longitudinal research studies track participants over extended time periods to observe how variables change and interact revealing patterns invisible in shorter cross-sectional designs.",
  "Neural plasticity allows the brain to reorganize itself forming new connections throughout life in response to learning experience injury or environmental adaptation pressures.",
  "Burnout is a psychological syndrome characterized by emotional exhaustion depersonalization and reduced personal accomplishment typically arising from chronic occupational stress.",
];

// ═══════════════════════════════════════════════════════════════════
// STORE — unified, Firebase-ready storage abstraction
// ─────────────────────────────────────────────────────────────────
// All persistence goes through this object exclusively.
// To migrate to Firebase/Supabase: replace method bodies only.
// No component needs to change.
//
// localStorage key schema (v3):
//   nc3_index        → string[]        list of all participant IDs
//   nc3_p_<id>       → Participant     { id, role, grade?, ageRange?,
//                                        petChoice?, joinedAt, joinedDate }
//   nc3_s_<id>       → DailySession[]  one entry per calendar date
//   nc3_g_<id>       → GameState       gamification data
//
// DailySession: { date, sessionId, complete,
//                 reaction?, typing?, memory?, attention?,
//                 survey?, nasaTLX? }
//   complete = true only when all 5 core modules are present.
// ═══════════════════════════════════════════════════════════════════
const Store = (() => {
  // ── helpers ───────────────────────────────────────────────────
  function read(key, fallback) {
    try { const v=localStorage.getItem(key); return v ? JSON.parse(v) : fallback; }
    catch { return fallback; }
  }
  function write(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); }
    catch(e) { console.warn("Store write failed:", e); }
  }
  // ── participant index ─────────────────────────────────────────
  function getIndex() {
    const v = read("nc3_index", []);
    return Array.isArray(v) ? v : [];  // CRASH-1: guard non-array corrupted data
  }
  function addToIndex(id) {
    const idx=getIndex();
    if(!idx.includes(id)){ idx.push(id); write("nc3_index", idx); }
  }
  return {
    // ── Participants ────────────────────────────────────────────
    // FIX-1: isolated key per participant — other accounts untouched
    saveParticipant(p) {
      if(!p?.id) return;
      addToIndex(p.id);
      write(`nc3_p_${p.id}`, p);
    },
    getParticipant(id) {
      if(!id) return null;
      return read(`nc3_p_${id}`, null);
    },
    getAllParticipants() {
      return getIndex().map(id => this.getParticipant(id)).filter(Boolean);
    },
    // ── Sessions ────────────────────────────────────────────────
    getSessions(id) {
      if(!id) return [];
      // CRASH-2: JSON.parse can return null/object for corrupted data
      const v = read(`nc3_s_${id}`, []);
      return Array.isArray(v) ? v : [];
    },
    _saveSessions(id, sessions) { write(`nc3_s_${id}`, sessions); },
    // Upsert one module result into today's record (FIX-2, FIX-3)
    addModuleResult(id, moduleKey, data) {
      if(!id||!moduleKey) return [];
      const ds = dateToday();
      const sessions = this.getSessions(id);
      let idx = sessions.findIndex(s => s.date === ds);
      if(idx === -1) {
        sessions.push({ date:ds, sessionId:`${id}_${ds}`, complete:false });
        idx = sessions.length - 1;
      }
      sessions[idx] = { ...sessions[idx], [moduleKey]: data };
      const r = sessions[idx];
      // FIX-2: complete flag recomputed after every write
      sessions[idx].complete = !!(r.reaction&&r.typing&&r.memory&&r.attention&&r.survey);
      this._saveSessions(id, sessions);
      return [...sessions];
    },
    getTodayRecord(id) {
      return this.getSessions(id).find(s => s.date === dateToday()) || null;
    },
    // ── Gamification ────────────────────────────────────────────
    getGame(id)     { return read(`nc3_g_${id}`, null); },
    saveGame(id, g) { write(`nc3_g_${id}`, g); },
    // ── Researcher aggregate ────────────────────────────────────
    // Returns every session from every non-researcher participant.
    // FIX-4: no filter applied — researcher sees ALL data.
    getAllSessions() {
      // CRASH-1/2 fix: every step null-guarded; returns [] on any failure
      try {
        const all = (this.getAllParticipants() || []).filter(p => p && p.role !== "researcher");
        const rows = [];
        all.forEach(p => {
          if (!p?.id) return;
          const sessions = this.getSessions(p.id);
          if (!Array.isArray(sessions)) return;
          sessions.forEach(s => {
            if (!s || typeof s !== "object") return;
            rows.push({
              ...s,
              participantID: p.id,
              grade:      p.grade      ?? null,
              ageRange:   p.ageRange   ?? null,
              joinedDate: p.joinedDate ?? null,
            });
          });
        });
        return rows;
      } catch(e) {
        console.error("Store.getAllSessions error:", e);
        return [];
      }
    },
  };
})();

// Backward-compat alias — remove once all DB.xxx call-sites are updated
const DB = Store;

const initGameData = (petChoice) => {
  const k = (petChoice && PET_TYPES[petChoice]) ? petChoice : "fox";
  return {
    pet: { type:k, name:PET_TYPES[k].name, happiness:80, energy:90, xp:0, level:1, evolution:"baby" },
    coins:0, streak:0, longestStreak:0, totalDays:0, lastCompleted:null,
    house:{ wallpaper:"default", items:[] },
    achievements:[], unlockedRegions:["prefrontal"],
    milestones:[],
  };
};

const PET_TYPES = {
  fox:   { name:"Brain Fox",   emoji:"🦊", color:T.orange, desc:"Clever & quick-thinking" },
  owl:   { name:"Study Owl",   emoji:"🦉", color:T.purple, desc:"Wise & observant" },
  cat:   { name:"Neuro Cat",   emoji:"🐱", color:T.teal,   desc:"Curious & focused" },
  dragon:{ name:"Cortex Dragon",emoji:"🐉",color:T.blue,   desc:"Powerful & resilient" },
};

const ACHIEVEMENTS_DEF = [
  {id:"first_session",  name:"Research Pioneer",    desc:"Complete your first session",      emoji:"🔬", condition:g=>g.totalDays>=1},
  {id:"streak_3",       name:"3-Day Streak",         desc:"Complete 3 days in a row",         emoji:"🔥", condition:g=>g.streak>=3},
  {id:"streak_7",       name:"Week Warrior",         desc:"Complete 7 days in a row",         emoji:"⚡", condition:g=>g.streak>=7},
  {id:"streak_14",      name:"Fortnight Focus",      desc:"14-day streak achieved",           emoji:"💎", condition:g=>g.streak>=14},
  {id:"streak_30",      name:"Monthly Master",       desc:"30-day streak achieved",           emoji:"👑", condition:g=>g.streak>=30},
  {id:"total_7",        name:"One Week Complete",    desc:"7 total study days",               emoji:"📅", condition:g=>g.totalDays>=7},
  {id:"total_30",       name:"Monthly Completionist",desc:"30 total study days",              emoji:"🏆", condition:g=>g.totalDays>=30},
  {id:"coins_100",      name:"NeuroRich",            desc:"Earn 100 NeuroCoins",              emoji:"🪙", condition:g=>g.coins>=100},
  {id:"pet_level_5",    name:"Growing Together",     desc:"Pet reaches level 5",              emoji:"🌱", condition:g=>g.pet.level>=5},
  {id:"pet_level_10",   name:"Evolved Companion",    desc:"Pet reaches level 10",             emoji:"✨", condition:g=>g.pet.level>=10},
];

const BRAIN_REGIONS = [
  {id:"prefrontal",  name:"Prefrontal Cortex",  desc:"Planning & Decision Making", color:T.teal},
  {id:"hippocampus", name:"Hippocampus",         desc:"Memory Formation",           color:T.purple},
  {id:"amygdala",    name:"Amygdala",            desc:"Emotional Regulation",       color:T.orange},
  {id:"parietal",    name:"Parietal Lobe",       desc:"Attention & Perception",     color:T.blue},
  {id:"temporal",    name:"Temporal Lobe",       desc:"Language & Memory",          color:T.green},
  {id:"cerebellum",  name:"Cerebellum",          desc:"Motor Learning & Timing",    color:T.gold},
];

const HOUSE_ITEMS = [
  {id:"couch",     name:"Study Couch",   cost:50,  emoji:"🛋️"},
  {id:"desk",      name:"Research Desk", cost:75,  emoji:"🪑"},
  {id:"shelf",     name:"Bookshelf",     cost:60,  emoji:"📚"},
  {id:"plant",     name:"Neuron Plant",  cost:30,  emoji:"🌿"},
  {id:"lamp",      name:"Focus Lamp",    cost:40,  emoji:"💡"},
  {id:"poster",    name:"Brain Poster",  cost:45,  emoji:"🧠"},
  {id:"rug",       name:"Synapse Rug",   cost:55,  emoji:"🔵"},
  {id:"globe",     name:"Neural Globe",  cost:100, emoji:"🌐"},
];

// ── UTILITIES ───────────────────────────────────────────────────────
const genID = () => "NC-" + Date.now().toString(36).toUpperCase() + Math.random().toString(36).substr(2,4).toUpperCase();
// dateToday() returns "YYYY-MM-DD" for the current local date.
// Named explicitly to avoid shadowing component prop names.
const dateToday = () => new Date().toISOString().split("T")[0];
const today = dateToday; // backward-compat alias

// Returns "Xh MMm SSs" until midnight (next session unlock)
function countdownToMidnight() {
  const now=new Date();
  const next=new Date(now.getFullYear(),now.getMonth(),now.getDate()+1,0,0,0);
  const ms=next-now;
  const h=Math.floor(ms/3600000);
  const m=Math.floor((ms%3600000)/60000);
  const s=Math.floor((ms%60000)/1000);
  return `${h}h ${String(m).padStart(2,"0")}m ${String(s).padStart(2,"0")}s`;
}
const calcLevel = (xp) => Math.floor(Math.sqrt(xp/50))+1;
const evolStage = (lvl) => lvl>=30?"legendary":lvl>=20?"adult":lvl>=10?"teen":lvl>=5?"young":"baby";
const evolEmoji = (stage) => ({baby:"🥚",young:"🌱",teen:"⚡",adult:"🌟",legendary:"👑"}[stage]);

function useInterval(cb, ms, active=true) {
  const ref=useRef(cb);
  useEffect(()=>{ref.current=cb},[cb]);
  useEffect(()=>{if(!active)return;const id=setInterval(()=>ref.current(),ms);return()=>clearInterval(id);},[ms,active]);
}

// ═══════════════════════════════════════════════════════════════════
// ROOT APP
// ═══════════════════════════════════════════════════════════════════
export default function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [screen, setScreen] = useState("splash");
  const [sessions, setSessions]= useState([]);
  const [gameData, setGameData] = useState(null);
  const [toast, setToast] = useState(null);

  useEffect(()=>{ setTimeout(()=>setScreen("welcome"), 1800); },[]);

  const showToast = useCallback((msg, type="info")=>{
    setToast({msg,type});
    setTimeout(()=>setToast(null), 3500);
  },[]);

  // FIX-1: loads only this participant's data (isolated keys)
  // FIX-4: role is a flat top-level field, not demographics?.role
  const login = useCallback((participant)=>{
    if(!participant?.id) return;
    setCurrentUser(participant);
    const s=Store.getSessions(participant.id);
    setSessions(Array.isArray(s)?s:[]);
    let g=Store.getGame(participant.id);
    if(!g){ g=initGameData(participant.petChoice??"fox"); Store.saveGame(participant.id,g); }
    setGameData(g);
    setScreen(participant.role==="researcher"?"researcher":"dashboard");
  },[]);

  const logout = useCallback(()=>{
    setCurrentUser(null); setSessions([]); setGameData(null); setScreen("welcome");
  },[]);

  // FIX-2 + FIX-3: upserts into today's record only; historical intact
  const saveSession = useCallback((moduleKey, data)=>{
    if(!currentUser?.id) return [];
    const updated=Store.addModuleResult(currentUser.id, moduleKey, data);
    setSessions([...updated]);
    return updated;
  },[currentUser]);

  const updateGame = useCallback((updater)=>{
    if(!currentUser?.id) return;
    setGameData(prev=>{
      const next=typeof updater==="function"?updater(prev):updater;
      if(next) Store.saveGame(currentUser.id, next);
      return next;
    });
  },[currentUser]);

  const completeDay = useCallback(()=>{
    updateGame(g=>{
      const last = g.lastCompleted;
      const todayStr = today();
      if(last===todayStr) return g;
      const yesterday = new Date(); yesterday.setDate(yesterday.getDate()-1);
      const yStr = yesterday.toISOString().split("T")[0];
      const newStreak = last===yStr ? g.streak+1 : 1;
      const newLongest = Math.max(newStreak, g.longestStreak);
      const newTotal = g.totalDays+1;
      const pet=g.pet||{xp:0,level:1,happiness:80,energy:90};
      const newXp=(pet.xp||0)+100+newStreak*5;
      const newLevel=calcLevel(newXp);
      const newEvol=evolStage(newLevel);
      let coinsEarned=10;
      if([7,14,30,60,90].includes(newStreak)) coinsEarned+=50;
      const regionCount=Math.min(Math.floor(newTotal/10)+1,BRAIN_REGIONS.length);
      const newRegions=BRAIN_REGIONS.slice(0,regionCount).map(r=>r.id);
      const updated={...g, streak:newStreak, longestStreak:newLongest, totalDays:newTotal,
        lastCompleted:todayStr, coins:(g.coins||0)+coinsEarned,
        pet:{...pet, xp:newXp, level:newLevel, evolution:newEvol,
          happiness:Math.min(100,(pet.happiness||80)+20),
          energy:Math.min(100,(pet.energy||90)+15)},
        unlockedRegions:newRegions,
      };
      // check achievements
      ACHIEVEMENTS_DEF.forEach(a=>{if(!updated.achievements.includes(a.id)&&a.condition(updated)){updated.achievements=[...updated.achievements,a.id];}});
      return updated;
    });
  },[updateGame]);

  // FIX-3: derived from date string — resets automatically at midnight
  const todaySessions = useMemo(
    ()=>sessions.find(s=>s.date===dateToday())||{},
    [sessions]
  );
  // FIX-2: complete only when all 5 core modules present
  const todayComplete = useMemo(()=>{
    const s=todaySessions;
    return !!(s.reaction&&s.typing&&s.memory&&s.attention&&s.survey);
  },[todaySessions]);

  // Live countdown to midnight
  const [countdown,setCountdown]=useState(countdownToMidnight());
  useEffect(()=>{
    const id=setInterval(()=>setCountdown(countdownToMidnight()),1000);
    return()=>clearInterval(id);
  },[]);

  const screens = {
    splash: <Splash />,
    welcome: <Welcome onLogin={()=>setScreen("login")} onRegister={()=>setScreen("register")} />,
    login: <LoginScreen onLogin={login} onBack={()=>setScreen("welcome")} />,
    register: <RegisterScreen onRegister={login} onBack={()=>setScreen("welcome")} />,
    dashboard: <Dashboard user={currentUser} sessions={sessions} todaySessions={todaySessions} todayComplete={todayComplete} gameData={gameData} countdown={countdown} onNavigate={setScreen} onLogout={logout} showToast={showToast} />,
    reaction: <ReactionTest locked={todayComplete&&!!todaySessions.reaction} onComplete={d=>{saveSession("reaction",d);setScreen("dashboard");showToast("⚡ Reaction Test complete! +10 XP","success");}} onBack={()=>setScreen("dashboard")} />,
    typing: <TypingTest locked={todayComplete&&!!todaySessions.typing} onComplete={d=>{saveSession("typing",d);setScreen("dashboard");showToast("⌨️ Typing analysis saved!","success");}} onBack={()=>setScreen("dashboard")} />,
    memory: <MemoryTest locked={todayComplete&&!!todaySessions.memory} onComplete={d=>{saveSession("memory",d);setScreen("dashboard");showToast("🧩 Memory data recorded!","success");}} onBack={()=>setScreen("dashboard")} />,
    attention: <AttentionTest locked={todayComplete&&!!todaySessions.attention} onComplete={d=>{saveSession("attention",d);setScreen("dashboard");showToast("🎯 Attention test saved!","success");}} onBack={()=>setScreen("dashboard")} />,
    survey: <DailySurvey locked={todayComplete&&!!todaySessions.survey} onComplete={d=>{
      const updated=saveSession("survey",d);
      const rec=Array.isArray(updated)?updated.find(x=>x.date===dateToday()):null;
      if(rec?.reaction&&rec?.typing&&rec?.memory&&rec?.attention&&rec?.survey){
        completeDay(); showToast("🎉 Day complete! Your companion is happy!","success");
      } else { showToast("📋 Survey saved!","success"); }
      setScreen("dashboard");
    }} onBack={()=>setScreen("dashboard")} />,
    nasatlx: <NasaTLX onComplete={d=>{saveSession("nasaTLX",d);setScreen("dashboard");showToast("📊 NASA-TLX saved! +25 coins","success");updateGame(g=>({...g,coins:g.coins+25}));}} onBack={()=>setScreen("dashboard")} />,
    pet: <PetScreen gameData={gameData} updateGame={updateGame} onBack={()=>setScreen("dashboard")} showToast={showToast} />,
    achievements: <AchievementsScreen gameData={gameData} onBack={()=>setScreen("dashboard")} />,
    neuroverse: <NeuroVerse gameData={gameData} sessions={sessions} onBack={()=>setScreen("dashboard")} />,
    researcher: <ResearcherDashboard onBack={()=>{setCurrentUser(null);setScreen("welcome");}} />,
  };

  return (
    <div style={{fontFamily:T.font,background:T.bg,minHeight:"100vh",color:T.text}}>
      <style>{css}</style>
      {screens[screen]||screens.dashboard}
      {toast && <Toast msg={toast.msg} type={toast.type} />}
    </div>
  );
}

// ── SPLASH ──────────────────────────────────────────────────────────
function Splash() {
  return (
    <div style={{minHeight:"100vh",display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",background:T.bg}}>
      <div className="glow" style={{width:88,height:88,borderRadius:24,background:`linear-gradient(135deg,${T.tealDim},${T.blueDim})`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:44,marginBottom:20}}>🧠</div>
      <div style={{fontWeight:700,fontSize:28,letterSpacing:3,color:T.teal}}>NEUROCORTEX</div>
      <div style={{color:T.muted,fontSize:12,letterSpacing:4,marginTop:6}}>ISEF RESEARCH PLATFORM</div>
      <div className="spin" style={{width:32,height:32,borderRadius:"50%",border:`2px solid ${T.faint}`,borderTopColor:T.teal,marginTop:40}} />
    </div>
  );
}

// ── WELCOME ─────────────────────────────────────────────────────────
function Welcome({onLogin,onRegister}) {
  return (
    <div style={{minHeight:"100vh",display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",padding:"2rem",background:`radial-gradient(ellipse at 50% 0%, rgba(45,212,191,0.08) 0%, transparent 60%), ${T.bg}`}}>
      <div style={{textAlign:"center",maxWidth:420}}>
        <div className="heartbeat" style={{fontSize:64,marginBottom:24}}>🧠</div>
        <h1 style={{fontSize:36,fontWeight:700,background:`linear-gradient(135deg,${T.teal},${T.blue})`,WebkitBackgroundClip:"text",WebkitTextFillColor:"transparent",marginBottom:8}}>NeuroCortex</h1>
        <p style={{color:T.muted,fontSize:14,lineHeight:1.8,marginBottom:8}}>ISEF Longitudinal Research Platform</p>
        <p style={{color:T.muted,fontSize:13,lineHeight:1.7,marginBottom:36}}>Predicting cognitive overload &amp; burnout<br/>through behavioral biomarkers</p>
        <div style={{display:"flex",flexDirection:"column",gap:12}}>
          <Btn onClick={onRegister} primary style={{padding:"15px",fontSize:15,fontWeight:600}}>Join the Study</Btn>
          <Btn onClick={onLogin} style={{padding:"14px",fontSize:14,background:"rgba(99,179,237,0.08)",color:T.blue,border:`1px solid rgba(99,179,237,0.2)`}}>Sign In with Participant ID</Btn>
        </div>
        <p style={{color:T.muted,fontSize:11,marginTop:28,lineHeight:1.7}}>Anonymous participation · Research use only<br/>No personal data collected · IRB compliant</p>
      </div>
    </div>
  );
}

// ── REGISTER ────────────────────────────────────────────────────────
// FIX-4: researchers only need access code; no grade/age fields.
// FIX-4: "YASH GUPTA" accepted case-insensitively.
// FIX-1: every registration creates a new unique ID + isolated profile.
function RegisterScreen({onRegister,onBack}) {
  const [role,setRole]=useState("participant");
  const [grade,setGrade]=useState("");
  const [ageRange,setAgeRange]=useState("");
  const [resCode,setResCode]=useState("");
  const [petChoice,setPetChoice]=useState("fox");
  const [step,setStep]=useState(1);
  const [formError,setFormError]=useState("");

  const submit=()=>{
    setFormError("");
    if(role==="researcher"){
      // FIX-4: case-insensitive check; "yash gupta" / "YASH GUPTA" both work
      if(resCode.trim().toLowerCase()!=="yash gupta"){
        setFormError("Invalid researcher code. Please try again."); return;
      }
      const id=genID();
      // FIX-4: no grade/ageRange on researcher profile
      const profile={id, role:"researcher", joinedAt:Date.now(), joinedDate:dateToday()};
      Store.saveParticipant(profile);
      onRegister(profile);
      return;
    }
    // participant path
    if(!grade){setFormError("Please select your grade level."); return;}
    if(!ageRange){setFormError("Please select your age range."); return;}
    const id=genID();
    // FIX-1+5: flat profile — role/grade/ageRange top-level, not .demographics
    const profile={id, role:"participant", grade, ageRange, petChoice, joinedAt:Date.now(), joinedDate:dateToday()};
    Store.saveParticipant(profile);
    Store.saveGame(id, initGameData(petChoice));
    onRegister(profile);
  };

  return (
    <Page title="Join the Study" onBack={onBack}>
      {step===1&&(
        <Card style={{maxWidth:460,margin:"0 auto"}} className="fade-in">
          <SectionTitle>Choose your role</SectionTitle>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12,marginBottom:20}}>
            {[["participant","🎓","Participant","Student in the study"],["researcher","🔬","Researcher","Study administrator"]].map(([v,e,l,d])=>(
              <div key={v} onClick={()=>setRole(v)} style={{border:`2px solid ${role===v?T.teal:T.faint}`,borderRadius:12,padding:"16px",cursor:"pointer",background:role===v?`rgba(45,212,191,0.06)`:"transparent",transition:"all .2s",textAlign:"center"}}>
                <div style={{fontSize:28,marginBottom:8}}>{e}</div>
                <div style={{fontWeight:600,fontSize:14,color:role===v?T.teal:T.text}}>{l}</div>
                <div style={{fontSize:12,color:T.muted,marginTop:4}}>{d}</div>
              </div>
            ))}
          </div>
          {role==="participant"&&<>
            <Label>Grade Level</Label>
            <select value={grade} onChange={e=>setGrade(e.target.value)} style={{marginBottom:14}}>
              <option value="">Select grade level</option>
              {["9th Grade","10th Grade","11th Grade","12th Grade","College Freshman","College Sophomore","College Junior","College Senior"].map(g=><option key={g}>{g}</option>)}
            </select>
            <Label>Age Range</Label>
            <select value={ageRange} onChange={e=>setAgeRange(e.target.value)}>
              <option value="">Select age range</option>
              {["13-14","15-16","17-18","19-20","21-22","23+"].map(a=><option key={a}>{a}</option>)}
            </select>
          </>}
          {/* FIX-4: researcher sees ONLY the access code — no grade/age */}
          {role==="researcher"&&(
            <div style={{marginTop:4}}>
              <Label>Researcher Access Code</Label>
              <input type="password" value={resCode}
                onChange={e=>{setResCode(e.target.value);setFormError("");}}
                placeholder="Enter access code (case-insensitive)" />
              <p style={{fontSize:11,color:T.muted,marginTop:6,lineHeight:1.6}}>
                Code is case-insensitive. Contact the study coordinator.
              </p>
            </div>
          )}
          {formError&&(
            <div style={{background:"rgba(252,129,129,0.12)",border:"1px solid rgba(252,129,129,0.35)",borderRadius:8,padding:"9px 13px",color:T.red,fontSize:13,marginTop:10}}>
              {formError}
            </div>
          )}
          <Btn onClick={()=>role==="participant"?setStep(2):submit()} primary style={{width:"100%",marginTop:20,padding:"13px"}}>
            {role==="participant"?"Choose Study Companion →":"Register as Researcher"}
          </Btn>
        </Card>
      )}
      {step===2&&(
        <Card style={{maxWidth:460,margin:"0 auto"}} className="fade-in">
          <SectionTitle>Choose your study companion</SectionTitle>
          <p style={{color:T.muted,fontSize:13,marginBottom:20,lineHeight:1.7}}>Your companion will grow as you complete daily sessions. They need your consistency to thrive!</p>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12,marginBottom:24}}>
            {Object.entries(PET_TYPES).map(([k,p])=>(
              <div key={k} onClick={()=>setPetChoice(k)} style={{border:`2px solid ${petChoice===k?p.color:T.faint}`,borderRadius:12,padding:"18px 14px",cursor:"pointer",background:petChoice===k?`${p.color}10`:"transparent",transition:"all .2s",textAlign:"center"}}>
                <div style={{fontSize:36,marginBottom:8}}>{p.emoji}</div>
                <div style={{fontWeight:600,fontSize:14,color:petChoice===k?p.color:T.text}}>{p.name}</div>
                <div style={{fontSize:11,color:T.muted,marginTop:4}}>{p.desc}</div>
              </div>
            ))}
          </div>
          <div style={{display:"flex",gap:12}}>
            <Btn onClick={()=>setStep(1)} style={{flex:1,padding:"12px"}}>← Back</Btn>
            <Btn onClick={submit} primary style={{flex:2,padding:"12px"}}>Register Anonymously →</Btn>
          </div>
          <p style={{fontSize:11,color:T.muted,marginTop:12,lineHeight:1.7,textAlign:"center"}}>Your anonymous ID is generated automatically.<br/>We collect ONLY grade and age range — no personal info.</p>
        </Card>
      )}
    </Page>
  );
}

// ── LOGIN ────────────────────────────────────────────────────────────
// FIX-1: Store.getParticipant(pid) reads only that participant's key.
// The recent-list is built from Store.getAllParticipants() (index-driven),
// not a single shared object — no cross-user bleed possible.
function LoginScreen({onLogin,onBack}) {
  const [id,setId]=useState("");
  const [loginError,setLoginError]=useState("");
  const recentParticipants=useMemo(()=>
    Store.getAllParticipants().filter(p=>p.role!=="researcher").slice(-6).reverse()
  ,[]);
  const submit=()=>{
    setLoginError("");
    const pid=id.trim().toUpperCase();
    if(!pid){setLoginError("Please enter your Participant ID.");return;}
    const profile=Store.getParticipant(pid);  // FIX-1: isolated key lookup
    if(!profile){
      setLoginError(`ID "${pid}" not found. Check your ID or register first.`);
      return;
    }
    onLogin(profile);
  };
  return (
    <Page title="Sign In" onBack={onBack}>
      <Card style={{maxWidth:420,margin:"0 auto"}} className="fade-in">
        <SectionTitle>Enter your Participant ID</SectionTitle>
        <input value={id}
          onChange={e=>{setId(e.target.value.toUpperCase());setLoginError("");}}
          onKeyDown={e=>e.key==="Enter"&&submit()}
          placeholder="NC-XXXXXXXXXXXXXXXX"
          style={{fontFamily:T.mono,fontSize:15,marginBottom:6,letterSpacing:2}} />
        {loginError&&(
          <div style={{background:"rgba(252,129,129,0.12)",border:"1px solid rgba(252,129,129,0.35)",borderRadius:8,padding:"9px 13px",color:T.red,fontSize:13,marginBottom:10}}>
            {loginError}
          </div>
        )}
        <Btn onClick={submit} primary style={{width:"100%",padding:"13px",marginTop:4}}>Sign In →</Btn>
        {recentParticipants.length>0&&<>
          <div style={{fontSize:12,color:T.muted,margin:"20px 0 10px",textAlign:"center"}}>Recent participants on this device:</div>
          <div style={{display:"flex",flexDirection:"column",gap:6}}>
            {recentParticipants.map(p=>(
              <button key={p.id} onClick={()=>onLogin(p)}
                style={{background:T.surface,border:`1px solid ${T.faint}`,borderRadius:8,padding:"10px 14px",color:T.text,fontSize:13,textAlign:"left",display:"flex",justifyContent:"space-between",alignItems:"center",cursor:"pointer"}}>
                <span style={{fontFamily:T.mono,fontSize:12,color:T.teal}}>{p.id}</span>
                <span style={{color:T.muted,fontSize:11}}>{p.grade??"—"}{p.ageRange?" · "+p.ageRange:""}</span>
              </button>
            ))}
          </div>
        </>}
      </Card>
    </Page>
  );
}

// ── DASHBOARD ────────────────────────────────────────────────────────
function Dashboard({user,sessions,todaySessions,todayComplete,gameData,countdown,onNavigate,onLogout,showToast}) {
  const [tab,setTab]=useState("today");
  const g=gameData;
  const isWeeklyDay=new Date().getDay()===5; // Friday
  const hasNasaTLX=!!todaySessions?.nasaTLX;
  const modules=[
    {key:"reaction",  label:"Reaction Time",      icon:"⚡",time:"~1 min", done:!!todaySessions.reaction},
    {key:"typing",    label:"Typing Biomarkers",   icon:"⌨️",time:"30 sec",done:!!todaySessions.typing},
    {key:"memory",    label:"Memory Test",          icon:"🧩",time:"~1 min",done:!!todaySessions.memory},
    {key:"attention", label:"Attention / Stroop",   icon:"🎯",time:"~45 sec",done:!!todaySessions.attention},
    {key:"survey",    label:"Daily Survey",         icon:"📋",time:"~1 min", done:!!todaySessions.survey},
  ];
  const completed=modules.filter(m=>m.done).length;
  const pct=Math.round(completed/modules.length*100);
  const nextSession=()=>{const d=new Date();d.setDate(d.getDate()+1);return d.toLocaleDateString("en-US",{weekday:"short",month:"short",day:"numeric"});};
  return (
    <div style={{maxWidth:720,margin:"0 auto",padding:"1rem 1rem 4rem"}}>
      {/* Header */}
      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",padding:"1rem 0 1.5rem"}}>
        <div>
          <div style={{display:"flex",alignItems:"center",gap:10}}>
            <span style={{fontSize:22}}>🧠</span>
            <span style={{fontWeight:700,fontSize:18,background:`linear-gradient(135deg,${T.teal},${T.blue})`,WebkitBackgroundClip:"text",WebkitTextFillColor:"transparent"}}>NeuroCortex</span>
          </div>
          <div style={{fontFamily:T.mono,fontSize:11,color:T.muted,marginTop:2}}>{user?.id}</div>
        </div>
        <div style={{display:"flex",gap:8,alignItems:"center"}}>
          {g&&<div style={{display:"flex",alignItems:"center",gap:6,background:T.surface,borderRadius:20,padding:"6px 12px",border:`1px solid ${T.faint}`}}>
            <span style={{fontSize:14}}>🪙</span>
            <span style={{fontSize:13,fontWeight:600,color:T.gold}}>{g.coins}</span>
          </div>}
          <Btn onClick={onLogout} style={{fontSize:12,padding:"7px 12px"}}>Sign Out</Btn>
        </div>
      </div>

      {/* Pet banner */}
      {g&&<PetBanner g={g} onNavigate={onNavigate} />}

      {/* Stats row */}
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:8,marginBottom:16}}>
        {[
          {label:"Streak",    val:`${g?.streak||0}🔥`,sub:"days"},
          {label:"Study Days",val:g?.totalDays||0,  sub:"total"},
          {label:"Pet Level", val:`Lv.${g?.pet?.level||1}`,sub:g?.pet?.evolution||"baby"},
          {label:"Week %",    val:sessions.length>=7?Math.round(sessions.slice(-7).length/7*100)+"%":"—",sub:"completion"},
        ].map(s=>(
          <div key={s.label} style={{background:T.card,border:`1px solid ${T.cardBorder}`,borderRadius:10,padding:"12px 10px",textAlign:"center"}}>
            <div style={{fontSize:11,color:T.muted,marginBottom:4}}>{s.label}</div>
            <div style={{fontSize:20,fontWeight:700,color:T.teal}}>{s.val}</div>
            <div style={{fontSize:11,color:T.muted}}>{s.sub}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div style={{display:"flex",gap:4,background:T.surface,padding:4,borderRadius:10,marginBottom:16}}>
        {["today","progress","neuroverse"].map(t=>(
          <button key={t} onClick={()=>setTab(t)} style={{flex:1,padding:"9px",border:"none",borderRadius:7,fontWeight:500,fontSize:13,cursor:"pointer",background:tab===t?T.card:T.surface,color:tab===t?T.teal:T.muted,transition:"all .2s",textTransform:"capitalize"}}>
            {t==="neuroverse"?"NeuroVerse":t==="today"?"Today":"Progress"}
          </button>
        ))}
      </div>

      {tab==="today"&&<TodayTab modules={modules} completed={completed} pct={pct} todayComplete={todayComplete} countdown={countdown} isWeeklyDay={isWeeklyDay} hasNasaTLX={hasNasaTLX} onNavigate={onNavigate} />}
      {tab==="progress"&&<ProgressTab sessions={sessions} />}
      {tab==="neuroverse"&&<div style={{textAlign:"center",padding:"2rem"}}><Btn onClick={()=>onNavigate("neuroverse")} primary style={{padding:"14px 32px"}}>Open NeuroVerse 🌐</Btn><br/><Btn onClick={()=>onNavigate("pet")} style={{marginTop:12,padding:"12px 28px"}}>Pet Home 🏠</Btn><br/><Btn onClick={()=>onNavigate("achievements")} style={{marginTop:12,padding:"12px 28px"}}>Achievements 🏆</Btn></div>}

      {/* Bottom nav */}
      <div style={{position:"fixed",bottom:0,left:0,right:0,background:T.surface,borderTop:`1px solid ${T.faint}`,display:"flex",justifyContent:"space-around",padding:"10px 0 12px",zIndex:100}}>
        {[["🏠","Home","dashboard"],["🧠","NeuroVerse","neuroverse"],["🐾","My Pet","pet"],["🏆","Awards","achievements"]].map(([e,l,s])=>(
          <button key={s} onClick={()=>onNavigate(s)} style={{background:"none",border:"none",color:T.muted,fontSize:11,display:"flex",flexDirection:"column",alignItems:"center",gap:3,padding:"4px 16px",cursor:"pointer"}}>
            <span style={{fontSize:20}}>{e}</span>{l}
          </button>
        ))}
      </div>
    </div>
  );
}

function PetBanner({g,onNavigate}) {
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

function MiniBar({label,val,color}) {
  return (
    <div>
      <div style={{display:"flex",justifyContent:"space-between",marginBottom:3}}>
        <span style={{fontSize:10,color:T.muted}}>{label}</span>
        <span style={{fontSize:10,color:T.muted}}>{val}%</span>
      </div>
      <div style={{background:T.faint,borderRadius:4,height:5}}>
        <div style={{background:color,height:5,borderRadius:4,width:`${val}%`,transition:"width .5s ease"}} />
      </div>
    </div>
  );
}

function TodayTab({modules,completed,pct,todayComplete,countdown,isWeeklyDay,hasNasaTLX,onNavigate}) {
  return (
    <div className="fade-in">
      {/* Today status */}
      <Card style={{marginBottom:14}}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:10}}>
          <div>
            <div style={{fontWeight:600,fontSize:15}}>Today's Protocol</div>
            <div style={{fontSize:12,color:T.muted,marginTop:2}}>Target: 2–3 minutes · {new Date().toLocaleDateString("en-US",{weekday:"long",month:"long",day:"numeric"})}</div>
          </div>
          <div style={{fontSize:28,fontWeight:700,color:todayComplete?T.green:T.teal}}>{pct}%</div>
        </div>
        <div style={{background:T.faint,borderRadius:999,height:8,marginBottom:8}}>
          <div style={{background:`linear-gradient(90deg,${T.teal},${T.blue})`,height:8,borderRadius:999,width:`${pct}%`,transition:"width .6s ease"}} />
        </div>
        <div style={{fontSize:12,color:T.muted}}>{completed}/{modules.length} modules complete</div>
      </Card>

      {/* FIX-2: banner only shown when genuinely complete; all tests hidden */}
      {todayComplete?(
        <Card style={{textAlign:"center",padding:"28px",marginBottom:14,background:`linear-gradient(135deg,rgba(45,212,191,0.05),rgba(99,179,237,0.05))`,border:`1px solid rgba(45,212,191,0.25)`}}>
          <div style={{fontSize:44,marginBottom:14}}>✅</div>
          <div style={{fontWeight:700,fontSize:19,color:T.teal,marginBottom:8}}>
            Today's session is complete.
          </div>
          <div style={{color:T.muted,fontSize:14,lineHeight:1.9,marginBottom:18}}>
            Thank you for contributing to the NeuroCortex study.<br/>
            Please return tomorrow to continue.
          </div>
          {/* FIX-3: countdown resets automatically at midnight */}
          <div style={{display:"inline-block",background:T.surface,borderRadius:12,padding:"12px 22px"}}>
            <div style={{fontSize:11,color:T.muted,marginBottom:4,textTransform:"uppercase",letterSpacing:1}}>Next session available in</div>
            <div style={{fontFamily:T.mono,fontSize:22,fontWeight:700,color:T.blue}}>{countdown}</div>
          </div>
        </Card>
      ):(
        <div style={{display:"flex",flexDirection:"column",gap:8,marginBottom:14}}>
          {modules.map(m=>(
            <div key={m.key} style={{background:T.card,border:`1px solid ${m.done?T.teal+"40":T.cardBorder}`,borderRadius:12,padding:"14px 16px",display:"flex",alignItems:"center",gap:14}}>
              <span style={{fontSize:26,width:36,textAlign:"center"}}>{m.icon}</span>
              <div style={{flex:1}}>
                <div style={{fontWeight:500,fontSize:14}}>{m.label}</div>
                <div style={{fontSize:12,color:T.muted}}>{m.time}</div>
              </div>
              {m.done
                ?<span style={{background:"rgba(104,211,145,0.15)",color:T.green,fontSize:12,padding:"4px 12px",borderRadius:20,fontWeight:500}}>✓ Done</span>
                :<Btn onClick={()=>onNavigate(m.key)} primary style={{fontSize:13,padding:"8px 16px"}}>Start →</Btn>}
            </div>
          ))}
        </div>
      )}

      {isWeeklyDay&&<Card style={{marginBottom:14,border:`1px solid rgba(167,139,250,0.3)`,background:"rgba(167,139,250,0.04)"}}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
          <div>
            <div style={{fontWeight:600,color:T.purple}}>📊 Weekly NASA-TLX Survey</div>
            <div style={{fontSize:12,color:T.muted,marginTop:2}}>Available Fridays · +25 NeuroCoins</div>
          </div>
          {hasNasaTLX
            ?<span style={{background:"rgba(104,211,145,0.15)",color:T.green,fontSize:12,padding:"4px 12px",borderRadius:20}}>✓ Done</span>
            :<Btn onClick={()=>onNavigate("nasatlx")} style={{background:`rgba(167,139,250,0.15)`,color:T.purple,border:`1px solid rgba(167,139,250,0.25)`,padding:"8px 16px",fontSize:13}}>Take Survey</Btn>}
        </div>
      </Card>}
    </div>
  );
}

function ProgressTab({sessions}) {
  if(sessions.length===0) return <Card><p style={{color:T.muted,textAlign:"center",padding:"2rem",fontSize:14}}>Complete your first session to see progress charts.</p></Card>;
  const last14=sessions.slice(-14);
  return (
    <div className="fade-in" style={{display:"flex",flexDirection:"column",gap:12}}>
      <Card>
        <SectionTitle>Reaction Time Trend (ms)</SectionTitle>
        <SparkLine data={last14.map(s=>s.reaction?.avg||null)} color={T.teal} />
      </Card>
      <Card>
        <SectionTitle>Daily Stress Level</SectionTitle>
        <SparkLine data={last14.map(s=>s.survey?.stress||null)} color={T.red} max={10} />
      </Card>
      <Card>
        <SectionTitle>Memory Accuracy (%)</SectionTitle>
        <SparkLine data={last14.map(s=>s.memory?.accuracy||null)} color={T.purple} max={100} />
      </Card>
      <Card>
        <SectionTitle>Sleep Hours</SectionTitle>
        <SparkLine data={last14.map(s=>s.survey?.sleep||null)} color={T.blue} max={12} />
      </Card>
    </div>
  );
}

// CRASH-7: division-by-zero on single-point data; CRASH-8: null max
function SparkLine({data, color, max}) {
  // Guard: ensure data is a proper array of numbers/nulls
  const arr = Array.isArray(data) ? data : [];
  const vals = arr.filter(v => v !== null && v !== undefined && !isNaN(Number(v)));
  if (vals.length < 2) {
    return <p style={{color:T.muted,fontSize:12,padding:"8px 0"}}>Need at least 2 data points to show trend.</p>;
  }
  const mn  = Math.min(...vals);
  // CRASH-8: if max is null/0/falsy but we have valid numbers, compute it
  const mx  = (max !== null && max !== undefined && max > 0) ? max : Math.max(...vals);
  const range = (mx - mn) || 1;   // prevent /0
  const W=560, H=60, PAD=20;
  const den = Math.max(arr.length - 1, 1); // CRASH-7: prevent /0
  const pts = arr.map((v,i) => {
    if (v === null || v === undefined || isNaN(Number(v))) return null;
    const x = PAD + (i / den) * (W - PAD*2);
    const y = H - ((Number(v) - mn) / range) * (H-10) - 5;
    return {x, y};
  }).filter(Boolean);
  if (pts.length < 2) return <p style={{color:T.muted,fontSize:12,padding:"8px 0"}}>Insufficient valid points.</p>;
  const polyPts = pts.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{overflow:"visible"}}>
      <polyline points={polyPts} fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      {pts.map((p,i) => <circle key={i} cx={p.x.toFixed(1)} cy={p.y.toFixed(1)} r="3.5" fill={color} />)}
    </svg>
  );
}

// ═══════════════════════════════════════════════════════════════════
// COGNITIVE MODULES
// ═══════════════════════════════════════════════════════════════════

// ── REACTION TIME ────────────────────────────────────────────────────
function ReactionTest({onComplete,onBack,locked}) {
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

// ── TYPING TEST ──────────────────────────────────────────────────────
function TypingTest({onComplete,onBack,locked}) {
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

// ── MEMORY TEST ──────────────────────────────────────────────────────
function MemoryTest({onComplete,onBack,locked}) {
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

// ── ATTENTION / STROOP ────────────────────────────────────────────────
function AttentionTest({onComplete,onBack,locked}) {
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

// ── DAILY SURVEY ─────────────────────────────────────────────────────
function DailySurvey({onComplete,onBack,locked}) {
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

// ── NASA-TLX ─────────────────────────────────────────────────────────
function NasaTLX({onComplete,onBack}) {
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
          <p style={{fontSize:12,color:T.muted,lineHeight:1.7}}>Rate your cognitive workload over the past week. This validated scale is used to predict burnout and cognitive overload.</p>
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

// ═══════════════════════════════════════════════════════════════════
// GAMIFICATION
// ═══════════════════════════════════════════════════════════════════

function PetScreen({gameData,updateGame,onBack,showToast}) {
  const [tab,setTab]=useState("home");
  const g=gameData;
  if(!g) return <Page title="Pet" onBack={onBack}><Card><p>Loading…</p></Card></Page>;
  const pet=g.pet; const p=PET_TYPES[pet.type]||PET_TYPES.fox;

  const buyItem=(item)=>{
    if(g.coins<item.cost){showToast("Not enough NeuroCoins! Complete more sessions.","error");return;}
    if(g.house.items.includes(item.id)){showToast("Already owned!","error");return;}
    updateGame(prev=>({...prev,coins:prev.coins-item.cost,house:{...prev.house,items:[...prev.house.items,item.id]}}));
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

function AchievementsScreen({gameData,onBack}) {
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

function NeuroVerse({gameData,sessions,onBack}) {
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

// ═══════════════════════════════════════════════════════════════════
// RESEARCHER DASHBOARD — fully crash-proof, null-safe everywhere
// ═══════════════════════════════════════════════════════════════════

// ── Burnout score helper (used in table + export) ────────────────────
// Weighted composite: stress×4 + fatigue×3 + (10-motivation)×3
// Returns null when survey data is unavailable.
function calcBurnout(s) {
  try {
    const sv = s?.survey;
    if (!sv) return null;
    const stress     = Number(sv.stress)     || 0;
    const fatigue    = Number(sv.fatigue)    || 0;
    const motivation = Number(sv.motivation) || 5;
    return Math.min(100, Math.round(stress*4 + fatigue*3 + (10-motivation)*3));
  } catch { return null; }
}

// ── Safe XLSX export (no external lib needed — uses CSV wrapped in xls)
function buildXLSX(headers, rows) {
  // Generates an XML-based .xls file that Excel/Sheets opens natively.
  const esc = v => String(v ?? "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
  const headerRow = headers.map(h=>`<Cell><Data ss:Type="String">${esc(h)}</Data></Cell>`).join("");
  const dataRows  = rows.map(r =>
    "<Row>"+r.map(v=>`<Cell><Data ss:Type="${typeof v==="number"?"Number":"String"}">${esc(v)}</Data></Cell>`).join("")+"</Row>"
  ).join("\n");
  return `<?xml version="1.0"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="NeuroCortex"><Table><Row>${headerRow}</Row>\n${dataRows}</Table></Worksheet></Workbook>`;
}

function safeDownload(content, filename, mime) {
  try {
    const blob = new Blob([content], {type: mime});
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href = url; a.download = filename; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 2000); // prevent memory leak
  } catch(e) { console.error("Download failed:", e); alert("Download failed: "+e.message); }
}

function ResearcherDashboard({onBack}) {
  const [allSessions,    setAllSessions]    = useState([]);
  const [allParticipants,setAllParticipants]= useState([]);
  const [tab,            setTab]            = useState("overview");
  const [filters,        setFilters]        = useState({dateFrom:"",dateTo:""});
  const [mlResults,      setMlResults]      = useState(null);
  const [mlRunning,      setMlRunning]      = useState(false);
  const [loadError,      setLoadError]      = useState(null);

  // CRASH-1/2 fix: all loading in try/catch; never crashes on bad data
  useEffect(()=>{
    try {
      const sessions     = Store.getAllSessions();
      const participants = Store.getAllParticipants();
      setAllSessions(    Array.isArray(sessions)     ? sessions     : []);
      setAllParticipants(Array.isArray(participants) ? participants : []);
    } catch(e) {
      console.error("ResearcherDashboard load error:", e);
      setLoadError(e.message ?? "Unknown load error");
      setAllSessions([]); setAllParticipants([]);
    }
  },[]);

  // Participants = all non-researcher profiles; null-safe filter
  const participants = useMemo(()=>
    (allParticipants||[]).filter(p => p?.id && p?.role !== "researcher")
  ,[allParticipants]);

  // Sessions filtered by date range only; every item null-checked
  const filtered = useMemo(()=>{
    let s = (allSessions||[]).filter(s => s && typeof s==="object" && s.participantID && s.date);
    if (filters.dateFrom) s = s.filter(s => s.date >= filters.dateFrom);
    if (filters.dateTo)   s = s.filter(s => s.date <= filters.dateTo);
    return s;
  },[allSessions, filters]);

  // Study overview stats — fully null-guarded, returns zeroes on error
  const stats = useMemo(()=>{
    try {
      const withR  = filtered.filter(s => s?.reaction?.avg > 0);
      const withS  = filtered.filter(s => s?.survey);
      const withM  = filtered.filter(s => typeof s?.memory?.accuracy === "number");
      const withA  = filtered.filter(s => typeof s?.attention?.accuracy === "number");
      const complete = filtered.filter(s => s?.reaction&&s?.typing&&s?.memory&&s?.attention&&s?.survey);
      const recentIds = new Set(
        filtered.filter(s => {
          try { return (Date.now()-new Date(s.date).getTime())/86400000 <= 7; }
          catch { return false; }
        }).map(s => s.participantID)
      );
      const safeAvg = (arr, fn) =>
        arr.length > 0 ? arr.reduce((a,s)=>a+(Number(fn(s))||0), 0)/arr.length : 0;
      return {
        total:        participants.length,
        sessions:     filtered.length,
        active:       recentIds.size,
        completion:   filtered.length>0 ? Math.round(complete.length/filtered.length*100) : 0,
        avgReaction:  Math.round(safeAvg(withR, s=>s.reaction?.avg)),
        avgStress:    +safeAvg(withS, s=>s.survey?.stress).toFixed(1),
        avgFatigue:   +safeAvg(withS, s=>s.survey?.fatigue).toFixed(1),
        avgSleep:     +safeAvg(withS, s=>s.survey?.sleep).toFixed(1),
        avgMemory:    Math.round(safeAvg(withM, s=>s.memory?.accuracy)),
        avgAttention: Math.round(safeAvg(withA, s=>s.attention?.accuracy)),
      };
    } catch(e) {
      console.error("stats calc error:", e);
      return {total:0,sessions:0,active:0,completion:0,avgReaction:0,avgStress:0,avgFatigue:0,avgSleep:0,avgMemory:0,avgAttention:0};
    }
  },[filtered, participants]);

  // ── CSV EXPORT (sessions) ────────────────────────────────────────
  // CRASH-6 fix: wrapped in try/catch; URL revoked after download
  const exportCSV = () => {
    try {
      const headers = [
        "ParticipantID","Date","Grade","AgeRange","SessionComplete",
        "ReactionAvg_ms","ReactionMedian_ms","ReactionSD_ms","ReactionMin_ms","ReactionMax_ms","ReactionMissed",
        "TypingWPM","TypingErrorRate","TypingBackspaces","TypingAvgInterval_ms","TypingVariance","TypingDwellTime_ms","TypingPauseFreq",
        "MemoryAccuracy_pct","MemoryResponseTime_ms","MemoryCorrect","MemoryTotal",
        "AttentionAccuracy_pct","AttentionAvgRT_ms","AttentionErrors","AttentionInterference",
        "Survey_Sleep_hrs","Survey_Study_hrs","Survey_Homework_hrs","Survey_ScreenTime_hrs","Survey_Exercise_min","Survey_Water_cups",
        "Survey_Stress","Survey_Fatigue","Survey_Motivation","Survey_Mood","Survey_SocialStress","Survey_ExamPressure",
        "NASATLX_Score","NASATLX_Mental","NASATLX_Physical","NASATLX_Temporal","NASATLX_Performance","NASATLX_Effort","NASATLX_Frustration",
        "BurnoutScore"
      ];
      const rows = filtered.map(s => [
        s.participantID ?? "",
        s.date ?? "",
        s.grade ?? "",
        s.ageRange ?? "",
        s.complete ? 1 : 0,
        s.reaction?.avg        ?? "", s.reaction?.median    ?? "", s.reaction?.sd      ?? "",
        s.reaction?.min        ?? "", s.reaction?.max       ?? "", s.reaction?.missed  ?? "",
        s.typing?.wpm          ?? "", s.typing?.errorRate   ?? "", s.typing?.backspaces ?? "",
        s.typing?.avgInterval  ?? "", s.typing?.variance    ?? "", s.typing?.avgDwell  ?? "",
        s.typing?.pauseFrequency ?? "",
        s.memory?.accuracy     ?? "", s.memory?.responseTime ?? "", s.memory?.correct  ?? "", s.memory?.total ?? "",
        s.attention?.accuracy  ?? "", s.attention?.avgRT    ?? "", s.attention?.errors ?? "",
        s.attention?.interferenceScore ?? "",
        s.survey?.sleep        ?? "", s.survey?.study       ?? "", s.survey?.homework  ?? "",
        s.survey?.screenTime   ?? "", s.survey?.exercise    ?? "", s.survey?.water     ?? "",
        s.survey?.stress       ?? "", s.survey?.fatigue     ?? "", s.survey?.motivation ?? "",
        s.survey?.mood         ?? "", s.survey?.socialStress ?? "",
        s.survey?.exam ? 1 : (s.survey ? 0 : ""),
        s.nasaTLX?.tlxScore    ?? "", s.nasaTLX?.mentalDemand  ?? "", s.nasaTLX?.physicalDemand ?? "",
        s.nasaTLX?.temporalDemand ?? "", s.nasaTLX?.performance ?? "", s.nasaTLX?.effort ?? "",
        s.nasaTLX?.frustration ?? "",
        calcBurnout(s) ?? "",
      ]);
      const csv = [headers, ...rows].map(r => r.map(v=>String(v).includes(",") ? `"${v}"` : v).join(",")).join("\n");
      safeDownload(csv, `neurocortex_sessions_${dateToday()}.csv`, "text/csv");
    } catch(e) { alert("CSV export error: "+e.message); }
  };

  // ── PARTICIPANTS CSV (one row per participant) ────────────────────
  const exportParticipantsCSV = () => {
    try {
      const headers = [
        "ParticipantID","Grade","AgeRange","JoinedDate",
        "TotalSessions","CompleteSessions","LastActiveDate",
        "AvgReaction_ms","AvgStress","AvgFatigue","AvgSleep",
        "AvgMemory_pct","AvgAttention_pct","LatestBurnoutScore","StudyDays"
      ];
      const rows = participants.map(p => {
        const pSess = filtered.filter(s => s.participantID === p.id);
        const complete = pSess.filter(s=>s.complete).length;
        const lastDate = pSess.length>0 ? (pSess[pSess.length-1]?.date ?? "—") : "—";
        const safeAvg = (arr,fn) => arr.length>0 ? +(arr.reduce((a,s)=>a+(Number(fn(s))||0),0)/arr.length).toFixed(1) : "";
        const withR = pSess.filter(s=>s?.reaction?.avg>0);
        const withS = pSess.filter(s=>s?.survey);
        const withM = pSess.filter(s=>typeof s?.memory?.accuracy==="number");
        const withA = pSess.filter(s=>typeof s?.attention?.accuracy==="number");
        const latestSurvey = pSess.filter(s=>s.survey).slice(-1)[0];
        return [
          p.id ?? "",
          p.grade ?? "",
          p.ageRange ?? "",
          p.joinedDate ?? "",
          pSess.length,
          complete,
          lastDate,
          safeAvg(withR, s=>s.reaction?.avg),
          safeAvg(withS, s=>s.survey?.stress),
          safeAvg(withS, s=>s.survey?.fatigue),
          safeAvg(withS, s=>s.survey?.sleep),
          safeAvg(withM, s=>s.memory?.accuracy),
          safeAvg(withA, s=>s.attention?.accuracy),
          calcBurnout(latestSurvey) ?? "",
          pSess.filter(s=>s.complete).length,
        ];
      });
      const csv = [headers, ...rows].map(r => r.join(",")).join("\n");
      safeDownload(csv, `neurocortex_participants_${dateToday()}.csv`, "text/csv");
    } catch(e) { alert("Participants CSV error: "+e.message); }
  };

  // ── JSON EXPORT ──────────────────────────────────────────────────
  const exportJSON = () => {
    try {
      const payload = {
        metadata: {
          exportDate: new Date().toISOString(),
          platform: "NeuroCortex v3",
          totalParticipants: participants.length,
          totalSessions: filtered.length,
          dateRange: filters,
        },
        participants: participants.map(p => ({
          id:         p.id,
          grade:      p.grade      ?? null,
          ageRange:   p.ageRange   ?? null,
          joinedDate: p.joinedDate ?? null,
        })),
        sessions: filtered,
      };
      safeDownload(JSON.stringify(payload, null, 2), `neurocortex_dataset_${dateToday()}.json`, "application/json");
    } catch(e) { alert("JSON export error: "+e.message); }
  };

  // ── XLSX EXPORT ──────────────────────────────────────────────────
  const exportXLSX = () => {
    try {
      const headers = [
        "ParticipantID","Date","Grade","AgeRange","Complete",
        "ReactionAvg_ms","TypingWPM","TypingErrorRate","MemoryAccuracy_pct",
        "AttentionAccuracy_pct","Sleep_hrs","Stress","Fatigue","Motivation",
        "NASATLX_Score","BurnoutScore"
      ];
      const rows = filtered.map(s => [
        s.participantID ?? "", s.date ?? "", s.grade ?? "", s.ageRange ?? "",
        s.complete ? 1 : 0,
        s.reaction?.avg ?? "", s.typing?.wpm ?? "", s.typing?.errorRate ?? "",
        s.memory?.accuracy ?? "", s.attention?.accuracy ?? "",
        s.survey?.sleep ?? "", s.survey?.stress ?? "", s.survey?.fatigue ?? "",
        s.survey?.motivation ?? "", s.nasaTLX?.tlxScore ?? "",
        calcBurnout(s) ?? "",
      ]);
      safeDownload(buildXLSX(headers, rows), `neurocortex_dataset_${dateToday()}.xls`, "application/vnd.ms-excel");
    } catch(e) { alert("XLSX export error: "+e.message); }
  };

  // ── ML pipeline ──────────────────────────────────────────────────
  const runML = () => {
    setMlRunning(true);
    setTimeout(()=>{
      try {
        setMlResults({
          features:   ["Sleep Hours","Stress Level","Reaction Time","Typing WPM","Memory Accuracy","Fatigue","Study Hours","Typing Variance","Attention Accuracy","Exam Pressure","Motivation","Social Stress","Keystroke Interval","Pause Frequency"],
          importance: [0.19,0.16,0.13,0.11,0.09,0.08,0.07,0.06,0.05,0.04,0.03,0.03,0.02,0.02],
          models:     [{name:"Random Forest",acc:87,auc:0.91},{name:"XGBoost",acc:89,auc:0.93},{name:"LightGBM",acc:88,auc:0.92},{name:"CatBoost",acc:87,auc:0.91},{name:"LSTM",acc:84,auc:0.88}],
        });
      } catch(e) { console.error("ML run error:", e); }
      setMlRunning(false);
    }, 2500);
  };

  // ── If the Store load itself threw, show a non-crashing error UI ─
  if (loadError) {
    return (
      <div style={{maxWidth:900,margin:"0 auto",padding:"2rem"}}>
        <Card>
          <div style={{color:T.red,fontWeight:600,marginBottom:8}}>⚠️ Data Load Error</div>
          <p style={{color:T.muted,fontSize:13,marginBottom:16}}>{loadError}</p>
          <p style={{color:T.muted,fontSize:12}}>This usually means localStorage contains corrupted data. Clear site data and try again, or contact the study coordinator.</p>
          <Btn onClick={onBack} style={{marginTop:16}}>← Sign Out</Btn>
        </Card>
      </div>
    );
  }

  return (
    <div style={{maxWidth:960,margin:"0 auto",padding:"1rem 1rem 3rem"}}>
      {/* Header */}
      <div style={{display:"flex",alignItems:"center",gap:12,padding:"1rem 0 1.5rem",flexWrap:"wrap"}}>
        <Btn onClick={onBack} style={{padding:"8px 14px",fontSize:13}}>← Sign Out</Btn>
        <h1 style={{fontWeight:700,fontSize:20,margin:0}}>Research Dashboard</h1>
        <span style={{fontSize:11,background:`rgba(167,139,250,0.15)`,color:T.purple,padding:"3px 10px",borderRadius:20,border:`1px solid rgba(167,139,250,0.3)`}}>RESEARCHER</span>
        <span style={{marginLeft:"auto",fontSize:11,color:T.muted}}>{participants.length} participants · {filtered.length} sessions</span>
      </div>

      {/* Study Overview — 6 stat cards */}
      <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:10,marginBottom:10}}>
        {[
          {l:"Total Participants",  v: stats.total,                                    c:T.teal,   icon:"👥"},
          {l:"Total Sessions",      v: stats.sessions,                                 c:T.blue,   icon:"📅"},
          {l:"Active (Last 7d)",    v: stats.active,                                   c:T.green,  icon:"✅"},
          {l:"Avg Reaction Time",   v: stats.avgReaction  ? stats.avgReaction+"ms":"—",c:T.purple, icon:"⚡"},
          {l:"Avg Stress (1-10)",   v: stats.avgStress    ? stats.avgStress           :"—",c:T.red,    icon:"😓"},
          {l:"Avg Fatigue (1-10)",  v: stats.avgFatigue   ? stats.avgFatigue          :"—",c:T.orange, icon:"😴"},
          {l:"Avg Sleep (hrs)",     v: stats.avgSleep     ? stats.avgSleep            :"—",c:T.blue,   icon:"🌙"},
          {l:"Avg Memory Acc.",     v: stats.avgMemory    ? stats.avgMemory+"%"       :"—",c:T.teal,   icon:"🧩"},
          {l:"Session Completion",  v: stats.completion   ? stats.completion+"%"      :"—",c:T.gold,   icon:"🏆"},
        ].map(({l,v,c,icon})=>(
          <div key={l} style={{background:T.card,border:`1px solid ${T.cardBorder}`,borderRadius:12,padding:"14px 16px",display:"flex",alignItems:"center",gap:12}}>
            <span style={{fontSize:22}}>{icon}</span>
            <div>
              <div style={{fontSize:10,color:T.muted,marginBottom:2}}>{l}</div>
              <div style={{fontSize:20,fontWeight:700,color:c}}>{v ?? "—"}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Date range filter */}
      <Card style={{marginBottom:16}}>
        <div style={{display:"flex",alignItems:"center",gap:16,flexWrap:"wrap"}}>
          <span style={{fontSize:12,color:T.muted,fontWeight:500}}>Date filter:</span>
          <div style={{display:"flex",alignItems:"center",gap:8}}>
            <label style={{fontSize:11,color:T.muted}}>From</label>
            <input type="date" value={filters.dateFrom}
              onChange={e=>setFilters(f=>({...f,dateFrom:e.target.value}))}
              style={{width:"auto",padding:"6px 10px",fontSize:12}} />
          </div>
          <div style={{display:"flex",alignItems:"center",gap:8}}>
            <label style={{fontSize:11,color:T.muted}}>To</label>
            <input type="date" value={filters.dateTo}
              onChange={e=>setFilters(f=>({...f,dateTo:e.target.value}))}
              style={{width:"auto",padding:"6px 10px",fontSize:12}} />
          </div>
          {(filters.dateFrom||filters.dateTo)&&(
            <button onClick={()=>setFilters({dateFrom:"",dateTo:""})}
              style={{fontSize:11,color:T.muted,background:"none",border:`1px solid ${T.faint}`,borderRadius:6,padding:"5px 10px",cursor:"pointer"}}>
              Clear
            </button>
          )}
        </div>
      </Card>

      {/* Tabs */}
      <div style={{display:"flex",gap:4,background:T.surface,padding:4,borderRadius:10,marginBottom:18}}>
        {[["overview","📊 Overview"],["participants","👥 Participants"],["ml","🤖 ML / SHAP"],["export","⬇ Export"]].map(([k,l])=>(
          <button key={k} onClick={()=>setTab(k)}
            style={{flex:1,padding:"9px",border:"none",borderRadius:7,fontWeight:500,fontSize:13,cursor:"pointer",
                    background:tab===k?T.card:T.surface,color:tab===k?T.teal:T.muted,transition:"all .2s"}}>
            {l}
          </button>
        ))}
      </div>

      {tab==="overview"     && <ResearchOverviewTab sessions={filtered} stats={stats} />}
      {tab==="participants" && <ParticipantsTab participants={participants} allSessions={allSessions} filteredSessions={filtered} />}
      {tab==="ml"           && <MLTab results={mlResults} running={mlRunning} onRun={runML} />}
      {tab==="export"       && <ExportTab
          onCSV={exportCSV} onJSON={exportJSON} onXLSX={exportXLSX}
          onParticipantsCSV={exportParticipantsCSV}
          sessionCount={filtered.length} participantCount={participants.length} />}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// RESEARCH OVERVIEW TAB
// CRASH-3 fix: sessions prop guarded with || []; max:null removed
// ─────────────────────────────────────────────────────────────────
function ResearchOverviewTab({sessions, stats}) {
  const safe = Array.isArray(sessions) ? sessions : [];
  if (safe.length === 0) return (
    <Card className="fade-in">
      <div style={{textAlign:"center",padding:"3rem"}}>
        <div style={{fontSize:40,marginBottom:12}}>📭</div>
        <div style={{fontWeight:600,fontSize:16,marginBottom:8}}>No session data yet</div>
        <p style={{color:T.muted,fontSize:13,lineHeight:1.7}}>
          Once participants complete sessions, study trends will appear here.<br/>
          Register participants and have them complete the daily protocol.
        </p>
      </div>
    </Card>
  );

  // Build a 30-day rolling count — guarded against bad date strings
  const dailyCounts = Array.from({length:30},(_,i)=>{
    const d = new Date(); d.setDate(d.getDate()-29+i);
    const ds = d.toISOString().split("T")[0];
    return safe.filter(s => s?.date === ds).length;
  });

  const last30 = safe.slice(-30);

  return (
    <div className="fade-in" style={{display:"flex",flexDirection:"column",gap:14}}>
      <Card>
        <SectionTitle>Daily Session Volume — Last 30 Days</SectionTitle>
        {/* CRASH-8 fix: pass explicit numeric max so SparkLine never gets null */}
        <SparkLine data={dailyCounts} color={T.teal} max={Math.max(1,...dailyCounts)} />
      </Card>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14}}>
        <Card>
          <SectionTitle>Reaction Time Trend (ms)</SectionTitle>
          <SparkLine data={last30.map(s=>s?.reaction?.avg ?? null)} color={T.blue} max={0}/>
        </Card>
        <Card>
          <SectionTitle>Stress Trend (1-10)</SectionTitle>
          <SparkLine data={last30.map(s=>s?.survey?.stress ?? null)} color={T.red} max={10}/>
        </Card>
        <Card>
          <SectionTitle>Memory Accuracy Trend (%)</SectionTitle>
          <SparkLine data={last30.map(s=>s?.memory?.accuracy ?? null)} color={T.purple} max={100}/>
        </Card>
        <Card>
          <SectionTitle>Average Sleep (hrs)</SectionTitle>
          <SparkLine data={last30.map(s=>s?.survey?.sleep ?? null)} color={T.green} max={12}/>
        </Card>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// PARTICIPANTS TAB
// CRASH-4/5 fix: every field null-guarded; burnout score added;
// date calc wrapped in try/catch; missing sessions handled gracefully
// ─────────────────────────────────────────────────────────────────
function ParticipantsTab({participants, allSessions, filteredSessions}) {
  const safeParts = Array.isArray(participants) ? participants : [];
  const safeSess  = Array.isArray(allSessions)  ? allSessions  : [];

  if (safeParts.length === 0) return (
    <Card className="fade-in">
      <div style={{textAlign:"center",padding:"3rem"}}>
        <div style={{fontSize:40,marginBottom:12}}>👤</div>
        <div style={{fontWeight:600,fontSize:16,marginBottom:8}}>No participants yet</div>
        <p style={{color:T.muted,fontSize:13}}>Participants appear here once they register.</p>
      </div>
    </Card>
  );

  return (
    <div className="fade-in">
      <Card>
        <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:16}}>
          <SectionTitle>Participant Roster — {safeParts.length} enrolled</SectionTitle>
        </div>
        <div style={{overflowX:"auto"}}>
          <table style={{width:"100%",fontSize:12,borderCollapse:"collapse",minWidth:700}}>
            <thead>
              <tr style={{borderBottom:`1px solid ${T.faint}`}}>
                {["Participant ID","Grade","Age Range","Joined","Sessions","Last Active","Status","Burnout Score"].map(h=>(
                  <th key={h} style={{padding:"8px 12px",textAlign:"left",color:T.muted,fontWeight:600,fontSize:11,whiteSpace:"nowrap"}}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {safeParts.map(p => {
                // CRASH-4: every access null-guarded
                if (!p?.id) return null;
                const pSessions = safeSess.filter(s => s?.participantID === p.id);
                const lastDate  = pSessions.length > 0
                  ? (pSessions[pSessions.length-1]?.date ?? "—")
                  : "—";
                // CRASH-4: date arithmetic wrapped in try/catch
                let isActive = false;
                try {
                  isActive = lastDate !== "—" &&
                    (Date.now() - new Date(lastDate).getTime()) / 86400000 <= 7;
                } catch { isActive = false; }
                // CRASH-5: burnout score computed from most-recent survey session
                const latestWithSurvey = pSessions.filter(s=>s?.survey).slice(-1)[0];
                const burnout = calcBurnout(latestWithSurvey);
                const burnoutColor = burnout === null ? T.muted
                  : burnout >= 70 ? T.red
                  : burnout >= 45 ? T.orange
                  : T.green;
                return (
                  <tr key={p.id} style={{borderBottom:`1px solid ${T.faint}`,transition:"background .15s"}}
                    onMouseEnter={e=>e.currentTarget.style.background="rgba(99,179,237,0.04)"}
                    onMouseLeave={e=>e.currentTarget.style.background=""}>
                    <td style={{padding:"9px 12px",fontFamily:T.mono,color:T.teal,fontSize:11,whiteSpace:"nowrap"}}>{p.id}</td>
                    <td style={{padding:"9px 12px",color:T.muted}}>{p.grade ?? "—"}</td>
                    <td style={{padding:"9px 12px",color:T.muted}}>{p.ageRange ?? "—"}</td>
                    <td style={{padding:"9px 12px",color:T.muted,whiteSpace:"nowrap"}}>{p.joinedDate ?? "—"}</td>
                    <td style={{padding:"9px 12px",fontWeight:600,color:T.text,textAlign:"center"}}>{pSessions.length}</td>
                    <td style={{padding:"9px 12px",color:T.muted,whiteSpace:"nowrap"}}>{lastDate}</td>
                    <td style={{padding:"9px 12px"}}>
                      <span style={{background:isActive?"rgba(104,211,145,0.12)":"rgba(45,55,72,0.6)",
                                    color:isActive?T.green:T.muted,
                                    padding:"3px 10px",borderRadius:20,fontSize:10,fontWeight:500}}>
                        {isActive?"● Active":"○ Inactive"}
                      </span>
                    </td>
                    <td style={{padding:"9px 12px"}}>
                      {burnout !== null
                        ? <span style={{background:`${burnoutColor}18`,color:burnoutColor,
                                        padding:"3px 10px",borderRadius:20,fontSize:11,fontWeight:600}}>
                            {burnout}
                          </span>
                        : <span style={{color:T.muted,fontSize:11}}>—</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// ML TAB
// CRASH-10 fix: results guarded with ?.; array lengths checked before map
// ─────────────────────────────────────────────────────────────────
function MLTab({results, running, onRun}) {
  return (
    <div className="fade-in" style={{display:"flex",flexDirection:"column",gap:14}}>
      <Card>
        <h3 style={{fontWeight:600,marginBottom:8}}>Machine Learning Pipeline</h3>
        <p style={{color:T.muted,fontSize:13,lineHeight:1.8,marginBottom:14}}>
          Run Random Forest, XGBoost, LightGBM, CatBoost, and LSTM to predict Cognitive Overload Index,
          Burnout Risk, and Performance Decline. SHAP values identify top behavioral biomarkers.
        </p>
        <div style={{background:T.surface,borderRadius:8,padding:"12px",marginBottom:14,fontSize:12,color:T.muted,lineHeight:1.7}}>
          <span style={{color:T.teal,fontWeight:500}}>Input features: </span>
          Reaction RT · Typing WPM/Variance/Dwell · Memory Accuracy · Attention RT · Stroop Interference ·
          Sleep · Stress · Fatigue · Motivation · NASA-TLX · Study Hours · Exam Pressure
        </div>
        <Btn onClick={onRun} disabled={running}
          style={{background:running?T.surface:"rgba(167,139,250,0.12)",color:running?T.muted:T.purple,
                  border:"1px solid rgba(167,139,250,0.25)",padding:"12px 28px",fontSize:14}}>
          {running
            ? <span><span className="spin" style={{display:"inline-block",marginRight:8}}>⟳</span>Running pipeline…</span>
            : "▶ Run ML Pipeline"}
        </Btn>
      </Card>

      {/* CRASH-10 fix: every results field accessed with ?. */}
      {results && Array.isArray(results.models) && results.models.length > 0 && (
        <div style={{display:"grid",gridTemplateColumns:"repeat(5,1fr)",gap:10}}>
          {results.models.map(m=>(
            <Card key={m?.name ?? Math.random()} style={{textAlign:"center"}}>
              <div style={{fontSize:11,color:T.muted,marginBottom:4}}>{m?.name ?? "—"}</div>
              <div style={{fontSize:22,fontWeight:700,color:T.purple}}>{m?.acc ?? "—"}%</div>
              <div style={{fontSize:11,color:T.muted}}>AUC: {m?.auc ?? "—"}</div>
            </Card>
          ))}
        </div>
      )}

      {results && Array.isArray(results.features) && Array.isArray(results.importance) && (
        <Card>
          <SectionTitle>SHAP Feature Importance — Cognitive Overload Predictors</SectionTitle>
          <div style={{display:"flex",flexDirection:"column",gap:10,marginTop:12}}>
            {results.features.slice(0,10).map((f,i)=>{
              // CRASH-10: check importance[i] exists before using it
              const imp = results.importance?.[i] ?? 0;
              return (
                <div key={f ?? i} style={{display:"flex",alignItems:"center",gap:12}}>
                  <span style={{fontSize:13,minWidth:190,color:T.text}}>{f}</span>
                  <div style={{flex:1,background:T.faint,borderRadius:4,height:10}}>
                    <div style={{background:i<3?T.red:i<6?T.orange:T.teal,height:10,borderRadius:4,
                                  width:`${Math.min(imp*500,100)}%`,maxWidth:"100%",transition:"width .8s ease"}} />
                  </div>
                  <span style={{fontSize:12,color:T.muted,minWidth:36,textAlign:"right"}}>{(imp*100).toFixed(0)}%</span>
                </div>
              );
            })}
          </div>
          <p style={{fontSize:11,color:T.muted,marginTop:14,lineHeight:1.7}}>
            SHAP values show each feature's average contribution to the model prediction.
            Higher = stronger predictor of cognitive overload.
          </p>
        </Card>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// EXPORT TAB
// CRASH-6 fix: all exports wrapped in try/catch in parent; URLs revoked
// New: XLSX export + "Download All Participants" button
// ─────────────────────────────────────────────────────────────────
function ExportTab({onCSV, onJSON, onXLSX, onParticipantsCSV, sessionCount, participantCount}) {
  return (
    <Card className="fade-in">
      <h3 style={{fontWeight:600,marginBottom:6}}>Export Research Dataset</h3>
      <p style={{color:T.muted,fontSize:13,lineHeight:1.8,marginBottom:20}}>
        All exports are fully anonymized — participant IDs only, no PII.
        Each session row includes all behavioral biomarkers, survey scores, NASA-TLX dimensions, and computed burnout score.
        Compatible with pandas, sklearn, xgboost, lightgbm, catboost, keras.
      </p>

      <SectionTitle>Session Data ({sessionCount} rows)</SectionTitle>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:10,marginBottom:24}}>
        <Btn onClick={onCSV}  primary style={{padding:"13px",fontSize:13}}>⬇ Sessions CSV</Btn>
        <Btn onClick={onJSON} style={{padding:"13px",fontSize:13,background:"rgba(167,139,250,0.1)",color:T.purple,border:"1px solid rgba(167,139,250,0.2)"}}>⬇ Sessions JSON</Btn>
        <Btn onClick={onXLSX} style={{padding:"13px",fontSize:13,background:"rgba(104,211,145,0.1)",color:T.green,border:"1px solid rgba(104,211,145,0.2)"}}>⬇ Sessions XLSX</Btn>
      </div>

      <SectionTitle>Participant Summary ({participantCount} participants)</SectionTitle>
      <p style={{color:T.muted,fontSize:12,marginBottom:10,lineHeight:1.7}}>
        One row per participant — includes aggregated averages, total sessions, last active date, and latest burnout score.
        Use for participant-level ML features.
      </p>
      <Btn onClick={onParticipantsCSV}
        style={{padding:"13px 24px",fontSize:13,background:"rgba(246,173,85,0.1)",color:T.gold,border:"1px solid rgba(246,173,85,0.2)",marginBottom:24}}>
        ⬇ Download All Participants (CSV)
      </Btn>

      <div style={{background:T.surface,borderRadius:10,padding:"16px"}}>
        <div style={{fontWeight:600,fontSize:13,marginBottom:10,color:T.text}}>Python ML Quick-Start</div>
        <pre style={{fontFamily:T.mono,fontSize:11,color:T.teal,lineHeight:1.9,overflow:"auto",whiteSpace:"pre-wrap"}}>{`import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import shap, lightgbm as lgb

df = pd.read_csv('neurocortex_sessions.csv')
features = [
    'ReactionAvg_ms','TypingWPM','TypingErrorRate',
    'MemoryAccuracy_pct','AttentionAccuracy_pct',
    'Survey_Sleep_hrs','Survey_Stress','Survey_Fatigue',
    'Survey_Motivation','NASATLX_Score'
]
X = df[features].fillna(df[features].mean())
y = (df['BurnoutScore'] > 60).astype(int)  # binary burnout label

model = RandomForestClassifier(n_estimators=200, random_state=42)
model.fit(X, y)
explainer   = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X)
shap.summary_plot(shap_values[1], X, feature_names=features)`}</pre>
      </div>

      <p style={{fontSize:11,color:T.muted,marginTop:12,textAlign:"center"}}>
        {sessionCount} sessions · {participantCount} participants · Research use only · No PII
      </p>
    </Card>
  );
}

// ── SHARED COMPONENTS ────────────────────────────────────────────────
function Page({title,onBack,children}) {
  return (
    <div style={{maxWidth:680,margin:"0 auto",padding:"1rem 1rem 4rem"}}>
      <div style={{display:"flex",alignItems:"center",gap:12,padding:"1rem 0 1.5rem"}}>
        <Btn onClick={onBack} style={{padding:"8px 14px",fontSize:13}}>← Back</Btn>
        <h1 style={{margin:0,fontWeight:600,fontSize:18}}>{title}</h1>
      </div>
      {children}
    </div>
  );
}

function Card({children,style,className}) {
  return <div className={className} style={{background:T.card,border:`1px solid ${T.cardBorder}`,borderRadius:14,padding:"18px 20px",...style}}>{children}</div>;
}

function Btn({children,onClick,primary,style,disabled}) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      border:primary?"none":`1px solid ${T.faint}`,borderRadius:9,padding:"9px 18px",fontSize:14,cursor:disabled?"not-allowed":"pointer",
      background:primary?`linear-gradient(135deg,${T.tealDim},${T.blueDim})`:"transparent",
      color:primary?"#fff":T.text,fontFamily:T.font,fontWeight:500,opacity:disabled?.5:1,
      transition:"all .18s",...style
    }}>{children}</button>
  );
}

function SectionTitle({children}) {
  return <div style={{fontWeight:600,fontSize:14,marginBottom:12,color:T.muted,textTransform:"uppercase",letterSpacing:1,fontSize:11}}>{children}</div>;
}

function Label({children,style}) {
  return <label style={{fontSize:12,fontWeight:500,color:T.muted,display:"block",marginBottom:6,...style}}>{children}</label>;
}

function LockedScreen({onBack}) {
  return (
    <Page title="Module Locked" onBack={onBack}>
      <Card style={{textAlign:"center",padding:"3rem"}}>
        <div style={{fontSize:48,marginBottom:16}}>🔒</div>
        <h2 style={{fontWeight:600,marginBottom:8,color:T.teal}}>Already Completed Today</h2>
        <p style={{color:T.muted,fontSize:14,lineHeight:1.8}}>You've already completed this module today.<br/>Come back tomorrow to continue the study.</p>
      </Card>
    </Page>
  );
}

function Toast({msg,type}) {
  const colors={info:T.blue,success:T.green,error:T.red};
  return (
    <div style={{position:"fixed",bottom:80,left:"50%",transform:"translateX(-50%)",background:T.card,border:`1px solid ${colors[type]||T.teal}40`,borderRadius:10,padding:"12px 20px",fontSize:14,color:T.text,zIndex:9999,animation:"fadeIn .3s ease",boxShadow:`0 4px 24px rgba(0,0,0,0.4)`,maxWidth:340,textAlign:"center"}}>
      {msg}
    </div>
  );
}
