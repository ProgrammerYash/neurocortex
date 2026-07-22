import { useState, useEffect, useCallback, useMemo } from 'react';
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { T } from './constants/tokens.js';
import { css } from './constants/styles.js';
import Store from './store/index.js';
import { fetchCurrentParticipant, getResearcherProfileFromToken, mapApiParticipantToProfile } from './store/auth.js';
import { getTokenRole } from './store/research.js';
import { ACHIEVEMENTS_DEF, BRAIN_REGIONS } from './constants/gamification.js';
import { dateToday, today, countdownToMidnight } from './utils/dates.js';
import { calcLevel, evolStage } from './utils/gamification.js';
import RegisterScreen from './components/auth/RegisterScreen.jsx';
import LoginScreen from './components/auth/LoginScreen.jsx';
import ResearcherSignInScreen from './components/auth/ResearcherSignInScreen.jsx';
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
import RouteFocusMain from './routing/RouteFocusMain.jsx';
import {
  BlockCrossRole,
  RedirectIfAuthed,
  RequireParticipant,
  RequireResearcher,
  shouldRestoreSession,
} from './routing/RouteGuards.jsx';
import { MODULE_SCREEN_TO_PATH, ROUTES } from './routing/routePaths.js';

export default function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [gameData, setGameData] = useState(null);
  const [toast, setToast] = useState(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const [sessionReady, setSessionReady] = useState(
    () => import.meta.env.VITE_USE_LOCAL_STORE === 'true',
  );

  const navigate = useNavigate();
  const location = useLocation();

  const showToast = useCallback((msg, type = 'info') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  }, []);

  const navigateAfterParticipantLogin = useCallback((participant) => {
    if (participant?.mustChangePin) {
      navigate(ROUTES.participantChangePin, { replace: true });
      return;
    }
    if (participant?.consentRequired === true || participant?.consentRecorded === false) {
      navigate(ROUTES.participantConsent, { replace: true });
      return;
    }
    navigate(ROUTES.participantDashboard, { replace: true });
  }, [navigate]);

  const loadParticipantSessionData = useCallback(async (profile) => {
    const s = await Store.getSessions(profile.id);
    setSessions(Array.isArray(s) ? s : []);
    const g = await Store.ensureGame(profile.id, profile.petChoice ?? 'fox');
    setGameData(g);
  }, []);

  useEffect(() => {
    if (import.meta.env.VITE_USE_LOCAL_STORE === 'true') {
      setSessionReady(true);
      return undefined;
    }
    if (!shouldRestoreSession(location.pathname)) {
      setSessionReady(true);
      return undefined;
    }
    let cancelled = false;
    setSessionReady(false);
    (async () => {
      const role = getTokenRole();
      if (!role || cancelled) {
        setSessionReady(true);
        return;
      }
      try {
        if (role === 'researcher') {
          const profile = getResearcherProfileFromToken();
          if (!profile?.id || cancelled) {
            setSessionReady(true);
            return;
          }
          setCurrentUser(profile);
          setSessions([]);
          setGameData(null);
          setSessionReady(true);
          return;
        }
        if (role === 'participant') {
          const me = await fetchCurrentParticipant();
          const profile = mapApiParticipantToProfile(me, me.public_id);
          if (cancelled) return;
          setCurrentUser(profile);
          if (!me.must_change_pin && me.consent_required !== true && me.consent_recorded !== false) {
            await loadParticipantSessionData(profile);
          } else {
            setSessions([]);
            setGameData(null);
          }
          setSessionReady(true);
        }
      } catch {
        if (!cancelled) {
          Store.clearAuth();
          setCurrentUser(null);
          setSessions([]);
          setGameData(null);
          setSessionReady(true);
        }
      }
    })();
    return () => { cancelled = true; };
  }, [location.pathname, loadParticipantSessionData]);

  const login = useCallback(async (participant) => {
    if (!participant?.id) return;
    setCurrentUser(participant);
    try {
      if (participant.role === 'researcher') {
        setSessions([]);
        setGameData(null);
        return;
      }
      if (participant.mustChangePin) {
        setSessions([]);
        setGameData(null);
        navigateAfterParticipantLogin(participant);
        return;
      }
      if (participant.consentRequired === true || participant.consentRecorded === false) {
        setSessions([]);
        setGameData(null);
        navigateAfterParticipantLogin(participant);
        return;
      }
      await loadParticipantSessionData(participant);
      navigateAfterParticipantLogin(participant);
    } catch (error) {
      Store.clearAuth();
      setCurrentUser(null);
      setSessions([]);
      setGameData(null);
      const message = error?.message || 'Could not load your account. Please try again.';
      showToast(message, 'error');
      throw error;
    }
  }, [loadParticipantSessionData, navigateAfterParticipantLogin, showToast]);

  const completePinChange = useCallback(async () => {
    const me = await fetchCurrentParticipant();
    const profile = mapApiParticipantToProfile(me, me.public_id);
    setCurrentUser(profile);
    if (me.consent_required === true || me.consent_recorded === false) {
      setSessions([]);
      setGameData(null);
      navigate(ROUTES.participantConsent, { replace: true });
      return;
    }
    await loadParticipantSessionData(profile);
    navigate(ROUTES.participantDashboard, { replace: true });
  }, [loadParticipantSessionData, navigate]);

  const completeExistingConsent = useCallback(async () => {
    const me = await fetchCurrentParticipant();
    if (me.consent_required === true || me.consent_recorded === false) {
      throw new Error('The server has not confirmed consent yet.');
    }
    const profile = mapApiParticipantToProfile(me, me.public_id);
    setCurrentUser(profile);
    await loadParticipantSessionData(profile);
    navigate(ROUTES.participantDashboard, { replace: true });
  }, [loadParticipantSessionData, navigate]);

  const logout = useCallback(() => {
    Store.clearAuth();
    setCurrentUser(null);
    setSessions([]);
    setGameData(null);
    navigate(ROUTES.home, { replace: true });
  }, [navigate]);

  const participantNavigate = useCallback((screenKey) => {
    const path = MODULE_SCREEN_TO_PATH[screenKey];
    if (path) navigate(path);
  }, [navigate]);

  const saveSession = useCallback(async (moduleKey, data) => {
    if (!currentUser?.id) return [];
    try {
      const updated = await Store.addModuleResult(currentUser.id, moduleKey, data);
      setSessions([...updated]);
      return updated;
    } catch (error) {
      const message = error?.message || 'Could not save session result.';
      showToast(message, 'error');
      throw error;
    }
  }, [currentUser, showToast]);

  const updateGame = useCallback(async (updater) => {
    if (!currentUser?.id) return;
    let nextValue;
    setGameData(prev => {
      nextValue = typeof updater === 'function' ? updater(prev) : updater;
      return nextValue;
    });
    if (nextValue) await Store.saveGame(currentUser.id, nextValue);
  }, [currentUser]);

  const completeDay = useCallback(async () => {
    await updateGame(g => {
      const last = g.lastCompleted;
      const todayStr = today();
      if (last === todayStr) return g;
      const yesterday = new Date(); yesterday.setDate(yesterday.getDate() - 1);
      const yStr = yesterday.toISOString().split('T')[0];
      const newStreak = last === yStr ? g.streak + 1 : 1;
      const newLongest = Math.max(newStreak, g.longestStreak);
      const newTotal = g.totalDays + 1;
      const pet = g.pet || { xp: 0, level: 1, happiness: 80, energy: 90 };
      const newXp = (pet.xp || 0) + 100 + newStreak * 5;
      const newLevel = calcLevel(newXp);
      const newEvol = evolStage(newLevel);
      let coinsEarned = 10;
      if ([7, 14, 30, 60, 90].includes(newStreak)) coinsEarned += 50;
      const regionCount = Math.min(Math.floor(newTotal / 10) + 1, BRAIN_REGIONS.length);
      const newRegions = BRAIN_REGIONS.slice(0, regionCount).map(r => r.id);
      const updated = {
        ...g, streak: newStreak, longestStreak: newLongest, totalDays: newTotal,
        lastCompleted: todayStr, coins: (g.coins || 0) + coinsEarned,
        pet: {
          ...pet, xp: newXp, level: newLevel, evolution: newEvol,
          happiness: Math.min(100, (pet.happiness || 80) + 20),
          energy: Math.min(100, (pet.energy || 90) + 15),
        },
        unlockedRegions: newRegions,
      };
      ACHIEVEMENTS_DEF.forEach(a => {
        if (!updated.achievements.includes(a.id) && a.condition(updated)) {
          updated.achievements = [...updated.achievements, a.id];
        }
      });
      return updated;
    });
  }, [updateGame]);

  const todaySessions = useMemo(
    () => sessions.find(s => s.date === dateToday()) || {},
    [sessions],
  );

  const todayComplete = useMemo(() => {
    const s = todaySessions;
    return !!(s.reaction && s.typing && s.memory && s.attention && s.survey);
  }, [todaySessions]);

  const [countdown, setCountdown] = useState(countdownToMidnight());
  useEffect(() => {
    const id = setInterval(() => setCountdown(countdownToMidnight()), 1000);
    return () => clearInterval(id);
  }, []);

  const maybeCompleteDay = useCallback(async (updated) => {
    const rec = Array.isArray(updated) ? updated.find(x => x.date === dateToday()) : null;
    if (rec?.reaction && rec?.typing && rec?.memory && rec?.attention && rec?.survey) {
      await completeDay();
      showToast('🎉 Daily Assessment Complete!', 'success');
      return true;
    }
    return false;
  }, [completeDay, showToast]);

  const waitingForSession = shouldRestoreSession(location.pathname) && !sessionReady;

  return (
    <div style={{ fontFamily: T.font, background: T.bg, minHeight: '100vh', color: T.text }}>
      <style>{css}</style>
      {waitingForSession ? null : (
        <RouteFocusMain>
          <Routes>
            <Route path={ROUTES.home} element={<PublicHome />} />
            <Route
              path={ROUTES.join}
              element={(
                <BlockCrossRole user={currentUser} expectedRole="participant">
                  <RedirectIfAuthed user={currentUser}>
                    <RegisterScreen onRegister={login} showToast={showToast} />
                  </RedirectIfAuthed>
                </BlockCrossRole>
              )}
            />
            <Route
              path={ROUTES.participantSignIn}
              element={(
                <BlockCrossRole user={currentUser} expectedRole="participant">
                  <RedirectIfAuthed user={currentUser}>
                    <LoginScreen onLogin={login} />
                  </RedirectIfAuthed>
                </BlockCrossRole>
              )}
            />
            <Route
              path={ROUTES.researcherSignIn}
              element={(
                <BlockCrossRole user={currentUser} expectedRole="researcher">
                  <RedirectIfAuthed user={currentUser}>
                    <ResearcherSignInScreen onLogin={login} />
                  </RedirectIfAuthed>
                </BlockCrossRole>
              )}
            />
            <Route
              path={ROUTES.participantChangePin}
              element={(
                <RequireParticipant user={currentUser} allowPinChangeOnly>
                  <ChangePinScreen onComplete={completePinChange} onLogout={logout} />
                </RequireParticipant>
              )}
            />
            <Route
              path={ROUTES.participantConsent}
              element={(
                <RequireParticipant user={currentUser} allowConsentOnly>
                  <ConsentCompletionScreen onComplete={completeExistingConsent} onLogout={logout} showToast={showToast} />
                </RequireParticipant>
              )}
            />
            <Route
              path={ROUTES.participantDashboard}
              element={(
                <RequireParticipant user={currentUser}>
                  <Dashboard user={currentUser} sessions={sessions} todaySessions={todaySessions} todayComplete={todayComplete} gameData={gameData} countdown={countdown} onNavigate={participantNavigate} onLogout={logout} showToast={showToast} unreadCount={unreadCount} onUnreadChange={setUnreadCount} />
                </RequireParticipant>
              )}
            />
            <Route
              path={ROUTES.participantInbox}
              element={(
                <RequireParticipant user={currentUser}>
                  <ParticipantInbox onBack={() => navigate(ROUTES.participantDashboard)} onUnreadChange={setUnreadCount} showToast={showToast} />
                </RequireParticipant>
              )}
            />
            <Route path={ROUTES.reaction} element={<RequireParticipant user={currentUser}><ReactionTest locked={!!todaySessions.reaction} onComplete={async d => { const updated = await saveSession('reaction', d); await maybeCompleteDay(updated); navigate(ROUTES.participantDashboard); showToast('⚡ Reaction Test complete! +10 XP', 'success'); }} onBack={() => navigate(ROUTES.participantDashboard)} /></RequireParticipant>} />
            <Route path={ROUTES.typing} element={<RequireParticipant user={currentUser}><TypingTest locked={!!todaySessions.typing} onComplete={async d => { const updated = await saveSession('typing', d); await maybeCompleteDay(updated); navigate(ROUTES.participantDashboard); showToast('⌨️ Typing analysis saved!', 'success'); }} onBack={() => navigate(ROUTES.participantDashboard)} /></RequireParticipant>} />
            <Route path={ROUTES.memory} element={<RequireParticipant user={currentUser}><MemoryTest locked={!!todaySessions.memory} onComplete={async d => { const updated = await saveSession('memory', d); await maybeCompleteDay(updated); navigate(ROUTES.participantDashboard); showToast('🧩 Memory data recorded!', 'success'); }} onBack={() => navigate(ROUTES.participantDashboard)} /></RequireParticipant>} />
            <Route path={ROUTES.attention} element={<RequireParticipant user={currentUser}><AttentionTest locked={!!todaySessions.attention} onComplete={async d => { const updated = await saveSession('attention', d); await maybeCompleteDay(updated); navigate(ROUTES.participantDashboard); showToast('🎯 Attention test saved!', 'success'); }} onBack={() => navigate(ROUTES.participantDashboard)} /></RequireParticipant>} />
            <Route path={ROUTES.survey} element={<RequireParticipant user={currentUser}><DailySurvey locked={!!todaySessions.survey} onComplete={async d => { const updated = await saveSession('survey', d); const finished = await maybeCompleteDay(updated); if (!finished) showToast('📋 Survey saved!', 'success'); navigate(ROUTES.participantDashboard); }} onBack={() => navigate(ROUTES.participantDashboard)} /></RequireParticipant>} />
            <Route path={ROUTES.nasaTlx} element={<RequireParticipant user={currentUser}><NasaTLX onComplete={async d => { await saveSession('nasaTLX', d); navigate(ROUTES.participantDashboard); showToast('📊 NASA-TLX saved! +25 coins', 'success'); await updateGame(g => ({ ...g, coins: g.coins + 25 })); }} onBack={() => navigate(ROUTES.participantDashboard)} /></RequireParticipant>} />
            <Route path={ROUTES.participantPet} element={<RequireParticipant user={currentUser}><PetScreen gameData={gameData} updateGame={updateGame} onBack={() => navigate(ROUTES.participantDashboard)} showToast={showToast} /></RequireParticipant>} />
            <Route path={ROUTES.participantAchievements} element={<RequireParticipant user={currentUser}><AchievementsScreen gameData={gameData} onBack={() => navigate(ROUTES.participantDashboard)} /></RequireParticipant>} />
            <Route path={ROUTES.participantNeuroverse} element={<RequireParticipant user={currentUser}><NeuroVerse gameData={gameData} sessions={sessions} onBack={() => navigate(ROUTES.participantDashboard)} /></RequireParticipant>} />
            <Route
              path={ROUTES.researcherDashboard}
              element={(
                <RequireResearcher user={currentUser}>
                  <ResearcherDashboard onBack={logout} showToast={showToast} />
                </RequireResearcher>
              )}
            />
            <Route path="*" element={<Navigate to={ROUTES.home} replace />} />
          </Routes>
        </RouteFocusMain>
      )}
      {toast && <Toast msg={toast.msg} type={toast.type} />}
    </div>
  );
}
