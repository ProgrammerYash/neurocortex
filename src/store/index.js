import { dateToday } from '../utils/dates.js';
import { genID } from '../utils/ids.js';
import {
  clearToken,
  fetchCurrentParticipant,
  loginResearcherWithApi,
  loginWithApi,
  mapApiParticipantToProfile,
  registerWithApi,
} from './auth.js';
import {
  fetchResearchParticipants,
  fetchResearchSessions,
  isResearcherAuthed,
} from './research.js';
import {
  fetchAllSessions,
  fetchTodaySession,
  upsertModuleResult,
} from './sessions.js';
import { fetchGameData, saveGameData } from './game.js';
import { initGameData } from './gameData.js';
import { addRecentParticipant } from './recentParticipants.js';

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
//   nc3_s_<id>       → DailySession[]  legacy local sessions (researcher/fallback)
//   nc3_g_<id>       → GameState       gamification data
//   nc3_token        → JWT access token (Phase 1C)
//
// DailySession: { date, sessionId, complete,
//                 reaction?, typing?, memory?, attention?,
//                 survey?, nasaTLX? }
//   complete = true only when all 5 core modules are present.
// ═══════════════════════════════════════════════════════════════════

function useLocalStore() {
  return import.meta.env.VITE_USE_LOCAL_STORE === 'true';
}

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

  function cacheParticipant(p) {
    if (!p?.id) return;
    addToIndex(p.id);
    write(`nc3_p_${p.id}`, p);
    if (p.role !== 'researcher') {
      addRecentParticipant(p);
    }
  }

  function _getSessionsLocal(id) {
    if(!id) return [];
    const v = read(`nc3_s_${id}`, []);
    return Array.isArray(v) ? v : [];
  }

  function _saveSessionsLocal(id, sessions) {
    write(`nc3_s_${id}`, sessions);
  }

  function _addModuleResultLocal(id, moduleKey, data) {
    if(!id||!moduleKey) return [];
    const ds = dateToday();
    const sessions = _getSessionsLocal(id);
    let idx = sessions.findIndex(s => s.date === ds);
    if(idx === -1) {
      sessions.push({ date:ds, sessionId:`${id}_${ds}`, complete:false });
      idx = sessions.length - 1;
    }
    sessions[idx] = { ...sessions[idx], [moduleKey]: data };
    const r = sessions[idx];
    sessions[idx].complete = !!(r.reaction&&r.typing&&r.memory&&r.attention&&r.survey);
    _saveSessionsLocal(id, sessions);
    return [...sessions];
  }

  function _getGameLocal(id) {
    if (!id) return null;
    return read(`nc3_g_${id}`, null);
  }

  function _saveGameLocal(id, gameData) {
    if (!id || !gameData) return;
    write(`nc3_g_${id}`, gameData);
  }

  return {
    // ── Auth (Phase 1C) ─────────────────────────────────────────
    clearAuth() {
      clearToken();
    },

    async registerParticipant(body) {
      if (useLocalStore()) {
        throw new Error('Electronic consent requires the study server. Local enrollment is unavailable.');
      }

      const data = await registerWithApi(body);
      const me = await fetchCurrentParticipant();
      const profile = mapApiParticipantToProfile(me, me.public_id);
      cacheParticipant(profile);
      return profile;
    },

    async loginParticipant({ publicId, pin }) {
      const pid = publicId?.trim().toUpperCase();
      if (!pid) throw new Error('Please enter your Participant ID.');

      if (useLocalStore()) {
        throw new Error('Participant sign-in requires the study server so consent status can be verified.');
      }

      await loginWithApi({ publicId: pid, pin });
      const me = await fetchCurrentParticipant();
      const profile = mapApiParticipantToProfile(me, me.public_id);
      cacheParticipant(profile);
      return profile;
    },

    async loginResearcher({ inviteCode }) {
      const code = inviteCode?.trim();
      if (!code) throw new Error('Please enter your access code.');

      if (useLocalStore()) {
        const id = genID();
        const profile = {
          id,
          role: 'researcher',
          displayName: 'Study Coordinator',
          joinedAt: Date.now(),
          joinedDate: dateToday(),
        };
        cacheParticipant(profile);
        return profile;
      }

      const data = await loginResearcherWithApi({ inviteCode });
      return {
        id: data.researcher_id,
        role: 'researcher',
        displayName: data.display_name,
        joinedAt: Date.now(),
        joinedDate: dateToday(),
      };
    },

    // ── Participants ────────────────────────────────────────────
    // FIX-1: isolated key per participant — other accounts untouched
    saveParticipant(p) {
      cacheParticipant(p);
    },
    getParticipant(id) {
      if(!id) return null;
      return read(`nc3_p_${id}`, null);
    },
    getLocalParticipants() {
      return getIndex().map(id => this.getParticipant(id)).filter(Boolean);
    },
    async getAllParticipants() {
      if (useLocalStore()) return this.getLocalParticipants();
      if (isResearcherAuthed()) return fetchResearchParticipants();
      return this.getLocalParticipants();
    },
    // ── Sessions ────────────────────────────────────────────────
    async getSessions(id) {
      if(!id) return [];
      if (isResearcherAuthed()) return [];
      if (useLocalStore()) return _getSessionsLocal(id);
      return fetchAllSessions();
    },
    async addModuleResult(id, moduleKey, data) {
      if(!id||!moduleKey) return [];
      if (useLocalStore()) return _addModuleResultLocal(id, moduleKey, data);
      await upsertModuleResult(dateToday(), moduleKey, data);
      return fetchAllSessions();
    },
    async getTodayRecord(id) {
      if(!id) return null;
      if (useLocalStore()) {
        return _getSessionsLocal(id).find(s => s.date === dateToday()) || null;
      }
      return fetchTodaySession();
    },
    // ── Gamification ────────────────────────────────────────────
    async getGame(id) {
      if (!id) return null;
      if (useLocalStore()) return _getGameLocal(id);

      const backend = await fetchGameData();
      if (backend) return backend;

      return _getGameLocal(id);
    },

    async saveGame(id, gameData) {
      if (!id || !gameData) return;
      if (useLocalStore()) {
        _saveGameLocal(id, gameData);
        return;
      }
      await saveGameData(gameData);
    },

    async ensureGame(id, petChoice = 'fox') {
      if (!id) return null;
      if (isResearcherAuthed()) return null;
      if (useLocalStore()) {
        let gameData = _getGameLocal(id);
        if (!gameData) {
          gameData = initGameData(petChoice);
          _saveGameLocal(id, gameData);
        }
        return gameData;
      }

      let gameData = await fetchGameData();
      if (gameData) return gameData;

      const localGameData = _getGameLocal(id);
      if (localGameData) {
        await saveGameData(localGameData);
        return localGameData;
      }

      gameData = initGameData(petChoice);
      await saveGameData(gameData);
      return gameData;
    },
    // ── Researcher aggregate ────────────────────────────────────
    // Returns every session from every non-researcher participant.
    // FIX-4: no filter applied — researcher sees ALL data.
    async getAllSessions() {
      if (useLocalStore()) {
        try {
          const all = (this.getLocalParticipants() || []).filter(p => p && p.role !== "researcher");
          const rows = [];
          all.forEach(p => {
            if (!p?.id) return;
            const sessions = _getSessionsLocal(p.id);
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
      }
      if (isResearcherAuthed()) return fetchResearchSessions();
      return [];
    },
  };
})();

// Backward-compat alias — remove once all DB.xxx call-sites are updated
export const DB = Store;
export default Store;
