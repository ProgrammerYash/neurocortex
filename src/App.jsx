import { useState, useEffect, useCallback, useMemo } from 'react';
import { T } from './constants/tokens.js';
import { css } from './constants/styles.js';
import Store from './store/index.js';
import { ACHIEVEMENTS_DEF, BRAIN_REGIONS } from './constants/gamification.js';
import { dateToday, today, countdownToMidnight } from './utils/dates.js';
import { calcLevel, evolStage } from './utils/gamification.js';
import Splash from './components/auth/Splash.jsx';
import Welcome from './components/auth/Welcome.jsx';
import RegisterScreen from './components/auth/RegisterScreen.jsx';
import LoginScreen from './components/auth/LoginScreen.jsx';
import Dashboard from './components/dashboard/Dashboard.jsx';
import ReactionTest from './components/modules/ReactionTest.jsx';
import TypingTest from './components/modules/TypingTest.jsx';
import MemoryTest from './components/modules/MemoryTest.jsx';
import AttentionTest from './components/modules/AttentionTest.jsx';
import DailySurvey from './components/modules/DailySurvey.jsx';
import NasaTLX from './components/modules/NasaTLX.jsx';
import PetScreen from './components/gamification/PetScreen.jsx';
import AchievementsScreen from './components/gamification/AchievementsScreen.jsx';
import NeuroVerse from './components/gamification/NeuroVerse.jsx';
import ResearcherDashboard from './components/research/ResearcherDashboard.jsx';
import Toast from './components/ui/Toast.jsx';

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
  const login = useCallback(async (participant)=>{
    if(!participant?.id) return;
    setCurrentUser(participant);
    const s=await Store.getSessions(participant.id);
    setSessions(Array.isArray(s)?s:[]);
    let g=await Store.ensureGame(participant.id, participant.petChoice??"fox");
    setGameData(g);
    setScreen(participant.role==="researcher"?"researcher":"dashboard");
  },[]);

  const logout = useCallback(()=>{
    Store.clearAuth();
    setCurrentUser(null); setSessions([]); setGameData(null); setScreen("welcome");
  },[]);

  // FIX-2 + FIX-3: upserts into today's record only; historical intact
  const saveSession = useCallback(async (moduleKey, data)=>{
    if(!currentUser?.id) return [];
    try {
      const updated=await Store.addModuleResult(currentUser.id, moduleKey, data);
      setSessions([...updated]);
      return updated;
    } catch (error) {
      const message = error?.message || 'Could not save session result.';
      showToast(message, 'error');
      throw error;
    }
  },[currentUser, showToast]);

  const updateGame = useCallback(async (updater)=>{
    if(!currentUser?.id) return;
    let nextValue;
    setGameData(prev=>{
      nextValue=typeof updater==="function"?updater(prev):updater;
      return nextValue;
    });
    if(nextValue) await Store.saveGame(currentUser.id, nextValue);
  },[currentUser]);

  const completeDay = useCallback(async ()=>{
    await updateGame(g=>{
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
    reaction: <ReactionTest locked={todayComplete&&!!todaySessions.reaction} onComplete={async d=>{await saveSession("reaction",d);setScreen("dashboard");showToast("⚡ Reaction Test complete! +10 XP","success");}} onBack={()=>setScreen("dashboard")} />,
    typing: <TypingTest locked={todayComplete&&!!todaySessions.typing} onComplete={async d=>{await saveSession("typing",d);setScreen("dashboard");showToast("⌨️ Typing analysis saved!","success");}} onBack={()=>setScreen("dashboard")} />,
    memory: <MemoryTest locked={todayComplete&&!!todaySessions.memory} onComplete={async d=>{await saveSession("memory",d);setScreen("dashboard");showToast("🧩 Memory data recorded!","success");}} onBack={()=>setScreen("dashboard")} />,
    attention: <AttentionTest locked={todayComplete&&!!todaySessions.attention} onComplete={async d=>{await saveSession("attention",d);setScreen("dashboard");showToast("🎯 Attention test saved!","success");}} onBack={()=>setScreen("dashboard")} />,
    survey: <DailySurvey locked={todayComplete&&!!todaySessions.survey} onComplete={async d=>{
      const updated=await saveSession("survey",d);
      const rec=Array.isArray(updated)?updated.find(x=>x.date===dateToday()):null;
      if(rec?.reaction&&rec?.typing&&rec?.memory&&rec?.attention&&rec?.survey){
        await completeDay(); showToast("🎉 Day complete! Your companion is happy!","success");
      } else { showToast("📋 Survey saved!","success"); }
      setScreen("dashboard");
    }} onBack={()=>setScreen("dashboard")} />,
    nasatlx: <NasaTLX onComplete={async d=>{await saveSession("nasaTLX",d);setScreen("dashboard");showToast("📊 NASA-TLX saved! +25 coins","success");await updateGame(g=>({...g,coins:g.coins+25}));}} onBack={()=>setScreen("dashboard")} />,
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
