import { apiRequest } from './apiClient.js';
import { dateToday } from '../utils/dates.js';

const TOKEN_KEY = 'nc3_token';

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token) {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch (error) {
    console.warn('Token save failed:', error);
  }
}

export function clearToken() {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch (error) {
    console.warn('Token clear failed:', error);
  }
}

export function getTokenPayload() {
  const token = getToken();
  if (!token) return null;
  try {
    return JSON.parse(atob(token.split('.')[1]));
  } catch {
    return null;
  }
}

export function getResearcherProfileFromToken() {
  const payload = getTokenPayload();
  if (!payload || payload.role !== 'researcher' || !payload.sub) return null;
  return {
    id: payload.sub,
    role: 'researcher',
    displayName: payload.display_name ?? 'Researcher',
    joinedAt: Date.now(),
    joinedDate: dateToday(),
  };
}

export function mapApiParticipantToProfile(participant, publicId) {
  const id = publicId || participant?.public_id;
  const joinedAt = participant?.joined_at
    ? new Date(participant.joined_at).getTime()
    : Date.now();
  const joinedDate = participant?.joined_at
    ? new Date(participant.joined_at).toISOString().split('T')[0]
    : dateToday();
  return {
    id,
    role: 'participant',
    grade: participant?.grade ?? null,
    ageRange: participant?.age_range ?? null,
    petChoice: participant?.pet_choice ?? 'fox',
    joinedAt,
    joinedDate,
  };
}

export async function registerWithApi({ grade, ageRange, ageConsentCategory, petChoice, pin, assentAcknowledged, parentalPermissionStatus, adultConsentAcknowledged }) {
  const data = await apiRequest('/v1/auth/participant/register', {
    method: 'POST',
    auth: false,
    body: {
      grade,
      age_range: ageRange,
      age_consent_category: ageConsentCategory ?? undefined,
      pet_choice: petChoice,
      pin,
      assent_acknowledged: assentAcknowledged ?? undefined,
      parental_permission_status: parentalPermissionStatus ?? undefined,
      adult_consent_acknowledged: adultConsentAcknowledged ?? undefined,
    },
  });
  setToken(data.access_token);
  return data;
}

export async function loginWithApi({ publicId, pin }) {
  const data = await apiRequest('/v1/auth/participant/login', {
    method: 'POST',
    auth: false,
    body: {
      public_id: publicId,
      pin,
    },
  });
  setToken(data.access_token);
  return data;
}

export async function fetchCurrentParticipant() {
  return apiRequest('/v1/participants/me');
}

export async function loginResearcherWithApi({ inviteCode }) {
  const data = await apiRequest('/v1/auth/researcher/login', {
    method: 'POST',
    auth: false,
    body: {
      invite_code: inviteCode,
    },
  });
  setToken(data.access_token);
  return data;
}
