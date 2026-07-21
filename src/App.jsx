import { useState, useEffect, useCallback, useMemo } from 'react';
import { T } from './constants/tokens.js';
import { css } from './constants/styles.js';
import Store from './store/index.js';
import { fetchCurrentParticipant, getResearcherProfileFromToken, mapApiParticipantToProfile } from './store/auth.js';
import { getTokenRole } from './store/research.js';
import { ACHIEVEMENTS_DEF, BRAIN_REGIONS } from './constants/gamification.js';
import { dateToday, today, countdownToMidnight } from './utils/dates.js';
import { calcLevel, evolStage } from './utils/gamification.js';
import Splash from './components/auth/Splash.jsx';
import Welcome from './components/auth/Welcome.jsx';
import RegisterScreen from './components/auth/RegisterScreen.jsx';
import LoginScreen from './components/auth/LoginScreen.jsx';
import Dashboard from './components/dashboard/Dashboard.jsx';
import ParticipantInbox from './components/dashboard/ParticipantInbox.jsx';
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
import ChangePinScreen from './components/auth/ChangePinScreen.jsx';
import ConsentCompletionScreen from './components/consent/ConsentCompletionScreen.jsx';
import PublicHome from './components/home/PublicHome.jsx';

export default function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [screen, setScreen] = useState("home");
  const [sessions, setSessions]= useState([]);
  const [gameData, setGameData] = useState(null);
  const [toast, setToast] = useState(null);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(()=>{
    if (import.meta.env.VITE_USE_LOCAL_STORE === 'true') return;
    let cancelled = false;
    (async ()=>{
      const role = getTokenRole();
      if (!role || cancelled) return;
      try {
        if (role === 'researcher') {
          const profile = getResearcherProfileFromToken();
          if (!profile?.id || cancelled) return;
          setCurrentUser(profile);
          setSessions([]);
          setGameData(null);
          setScreen('researcher');
          return;
        }
        if (role === 'participant') {
          const me = await fetchCurrentParticipant();
          const profile = mapApiParticipantToProfile(me, me.public_id);
          if (cancelled) return;
          setCurrentUser(profile);
          if (me.must_change_pin) {
            setSessions([]);
            setGameData(null);
            setScreen('change-pin');
            return;
          }
          if (me.consent_required === true || me.consent_recorded === false) {
            setSessions([]);
            setGameData(null);
            setScreen('consent');
            return;
          }
          const s = await Store.getSessions(profile.id);
          setSessions(Array.isArray(s) ? s : []);
          const g = await Store.ensureGame(profile.id, profile.petChoice ?? 'fox');
          setGameData(g);
          setScreen('dashboard');
        }
      } catch {
        if (!cancelled) {
          Store.clearAuth();
        }
      }
    })();
    return ()=>{ cancelled = true; };
  },[]);

  const showToast = useCallback((msg, type="info")=>{
    setToast({msg,type});
    setTimeout(()=>setToast(null), 3500);
  },[]);

  // FIX-1: loads only this participant's data (isolated keys)
  // FIX-4: role is a flat top-level field, not demographics?.role
  const login = useCallback(async (participant)=>{
    if(!participant?.id) return;
    setCurrentUser(participant);
    try {
      if (participant.role === 'researcher') {
        setSessions([]);
        setGameData(null);
        setScreen('researcher');
        return;
      }
      if (participant.mustChangePin) {
        setSessions([]);
        setGameData(null);
        setScreen('change-pin');
        return;
      }
      if (participant.consentRequired === true || participant.consentRecorded === false) {
        setSessions([]);
        setGameData(null);
        setScreen('consent');
        return;
      }
      const s=await Store.getSessions(participant.id);
      setSessions(Array.isArray(s)?s:[]);
      const g=await Store.ensureGame(participant.id, participant.petChoice??"fox");
      setGameData(g);
      setScreen('dashboard');
    } catch (error) {
      Store.clearAuth();
      setCurrentUser(null);
      setSessions([]);
      setGameData(null);
      const message = error?.message || 'Could not load your account. Please try again.';
      showToast(message, 'error');
      throw error;
    }
  },[showToast]);

  const completePinChange = useCallback(async ()=>{
    const me = await fetchCurrentParticipant();
    const profile = mapApiParticipantToProfile(me, me.public_id);
    setCurrentUser(profile);
    if (me.consent_required === true || me.consent_recorded === false) {
      setSessions([]);
      setGameData(null);
      setScreen('consent');
      return;
    }
    const s = await Store.getSessions(profile.id);
    setSessions(Array.isArray(s)?s:[]);
    setGameData(await Store.ensureGame(profile.id, profile.petChoice??'fox'));
    setScreen('dashboard');
  },[]);

  const completeExistingConsent = useCallback(async ()=>{
    const me = await fetchCurrentParticipant();
    if (me.consent_required === true || me.consent_recorded === false) {
      throw new Error('The server has not confirmed consent yet.');
    }
    const profile = mapApiParticipantToProfile(me, me.public_id);
    setCurrentUser(profile);
    const s = await Store.getSessions(profile.id);
    setSessions(Array.isArray(s)?s:[]);
    setGameData(await Store.ensureGame(profile.id, profile.petChoice??'fox'));
    setScreen('dashboard');
  },[]);

  const logout = useCallback(()=>{
    Store.clearAuth();
    setCurrentUser(null); setSessions([]); setGameData(null); setScreen("home");
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

  const maybeCompleteDay = useCallback(async (updated) => {
    const rec = Array.isArray(updated) ? updated.find(x => x.date === dateToday()) : null;
    if (rec?.reaction && rec?.typing && rec?.memory && rec?.attention && rec?.survey) {
      await completeDay();
      showToast("🎉 Daily Assessment Complete!", "success");
      return true;
    }
    return false;
  }, [completeDay, showToast]);

  const screens = {
    splash: <Splash />,
    home: (
      <PublicHome
        onJoinStudy={() => setScreen('register')}
        onSignIn={() => setScreen('login')}
        onResearcherAccess={() => setScreen('register')}
      />
    ),
    welcome: <Welcome onLogin={()=>setScreen("login")} onRegister={()=>setScreen("register")} />,
    login: <LoginScreen onLogin={login} onBack={()=>setScreen("home")} />,
    register: <RegisterScreen onRegister={login} onBack={()=>setScreen("home")} showToast={showToast} />,
    consent: <ConsentCompletionScreen onComplete={completeExistingConsent} onLogout={logout} showToast={showToast} />,
    'change-pin': <ChangePinScreen onComplete={completePinChange} onLogout={logout} />,
    dashboard: <Dashboard user={currentUser} sessions={sessions} todaySessions={todaySessions} todayComplete={todayComplete} gameData={gameData} countdown={countdown} onNavigate={setScreen} onLogout={logout} showToast={showToast} unreadCount={unreadCount} onUnreadChange={setUnreadCount} />,
    inbox: <ParticipantInbox onBack={() => setScreen('dashboard')} onUnreadChange={setUnreadCount} showToast={showToast} />,
    reaction: <ReactionTest locked={!!todaySessions.reaction} onComplete={async d=>{const updated=await saveSession("reaction",d);await maybeCompleteDay(updated);setScreen("dashboard");showToast("⚡ Reaction Test complete! +10 XP","success");}} onBack={()=>setScreen("dashboard")} />,
    typing: <TypingTest locked={!!todaySessions.typing} onComplete={async d=>{const updated=await saveSession("typing",d);await maybeCompleteDay(updated);setScreen("dashboard");showToast("⌨️ Typing analysis saved!","success");}} onBack={()=>setScreen("dashboard")} />,
    memory: <MemoryTest locked={!!todaySessions.memory} onComplete={async d=>{const updated=await saveSession("memory",d);await maybeCompleteDay(updated);setScreen("dashboard");showToast("🧩 Memory data recorded!","success");}} onBack={()=>setScreen("dashboard")} />,
    attention: <AttentionTest locked={!!todaySessions.attention} onComplete={async d=>{const updated=await saveSession("attention",d);await maybeCompleteDay(updated);setScreen("dashboard");showToast("🎯 Attention test saved!","success");}} onBack={()=>setScreen("dashboard")} />,
    survey: <DailySurvey locked={!!todaySessions.survey} onComplete={async d=>{
      const updated=await saveSession("survey",d);
      const finished = await maybeCompleteDay(updated);
      if (!finished) showToast("📋 Survey saved!","success");
      setScreen("dashboard");
    }} onBack={()=>setScreen("dashboard")} />,
    nasatlx: <NasaTLX onComplete={async d=>{await saveSession("nasaTLX",d);setScreen("dashboard");showToast("📊 NASA-TLX saved! +25 coins","success");await updateGame(g=>({...g,coins:g.coins+25}));}} onBack={()=>setScreen("dashboard")} />,
    pet: <PetScreen gameData={gameData} updateGame={updateGame} onBack={()=>setScreen("dashboard")} showToast={showToast} />,
    achievements: <AchievementsScreen gameData={gameData} onBack={()=>setScreen("dashboard")} />,
    neuroverse: <NeuroVerse gameData={gameData} sessions={sessions} onBack={()=>setScreen("dashboard")} />,
    researcher: <ResearcherDashboard onBack={logout} showToast={showToast} />,
  };

  return (
    <div style={{fontFamily:T.font,background:T.bg,minHeight:"100vh",color:T.text}}>
      <style>{css}</style>
      {screens[screen]||screens.home}
      {toast && <Toast msg={toast.msg} type={toast.type} />}
    </div>
  );
}
