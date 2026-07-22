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
    consentRequired: participant?.consent_required == null ? undefined : participant.consent_required === true,
    consentRecorded: participant?.consent_recorded == null ? undefined : participant.consent_recorded === true,
    mustChangePin: participant?.must_change_pin === true,
    joinedAt,
    joinedDate,
  };
}

export async function registerWithApi(body) {
  const data = await apiRequest('/v1/auth/participant/register', {
    method: 'POST',
    auth: false,
    body: {
      grade: body.grade,
      age_range: body.ageRange,
      age_consent_category: body.ageConsentCategory,
      pet_choice: body.petChoice,
      pin: body.pin,
      pin_confirmation: body.pinConfirmation,
      participant_printed_name: body.participantPrintedName,
      guardian_printed_name: body.guardianPrintedName,
      participant_acknowledged: body.participantAcknowledged,
      guardian_acknowledged: body.guardianAcknowledged,
      participant_signature_png: body.participantSignaturePng,
      guardian_signature_png: body.guardianSignaturePng,
      consent_version: body.consentVersion,
      survey_version: body.surveyVersion,
      template_sha256: body.templateSha256,
      idempotency_key: body.idempotencyKey,
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

export async function changePinWithApi({ pin, pinConfirmation }) {
  const data = await apiRequest('/v1/auth/participant/change-pin', {
    method: 'POST',
    body: {
      pin,
      pin_confirmation: pinConfirmation,
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

export async function fetchRecentParticipantStatus(publicIds) {
  const data = await apiRequest('/v1/auth/participant/recent-status', {
    method: 'POST',
    auth: false,
    body: { public_ids: publicIds },
  });
  return Array.isArray(data?.participants) ? data.participants : [];
}
