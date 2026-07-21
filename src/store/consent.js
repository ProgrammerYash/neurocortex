import { apiBlob, apiRequest } from './apiClient.js';

export async function fetchCurrentConsent() {
  return apiRequest('/v1/consent/current', { auth: false });
}

export async function fetchMyConsentStatus() {
  return apiRequest('/v1/participants/me/consent-status');
}

export async function submitMyConsent(body) {
  return apiRequest('/v1/participants/me/consent', { method: 'POST', body: toConsentApiBody(body) });
}

export function toConsentApiBody(body) {
  return {
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
  };
}

export function fetchResearcherConsents({ limit = 20, offset = 0, search = '', sort = 'participant_signed_at', direction = 'desc' } = {}) {
  const query = new URLSearchParams({
    limit:String(limit),
    offset:String(offset),
    search,
    sort_order:direction,
  });
  return apiRequest(`/v1/researcher/consents?${query}`);
}

export function fetchConsentPdf(id) {
  return apiBlob(`/v1/researcher/consents/${encodeURIComponent(id)}/pdf`, {
    filenameFallback: 'consent.pdf',
  });
}

export function downloadConsent(id) {
  return apiBlob(`/v1/researcher/consents/${encodeURIComponent(id)}/download`, {
    filenameFallback: 'consent.pdf',
  });
}

export function downloadAllConsents() {
  return apiBlob('/v1/researcher/consents/download-all', {
    filenameFallback: 'neurocortex-consents.zip',
  });
}

export async function withdrawParticipation() {
  return apiRequest('/v1/participants/me/withdraw', { method: 'POST' });
}

export async function requestDataDeletion() {
  return apiRequest('/v1/participants/me/request-data-deletion', { method: 'POST' });
}

export async function fetchMyStudyProgress() {
  return apiRequest('/v1/participants/me/study-progress');
}

export async function fetchEnrollmentStatus() {
  return apiRequest('/v1/research/enrollment-status');
}

export async function resolveAgeConsentCategory(publicId, ageConsentCategory) {
  return apiRequest(`/v1/research/participants/${publicId}/resolve-age-category`, {
    method: 'POST',
    body: { age_consent_category: ageConsentCategory },
  });
}

export async function fetchParticipantConsentStatus(publicId) {
  return apiRequest(`/v1/research/participants/${publicId}/consent-status`);
}

export async function recordResearcherConsentEvent(publicId, body) {
  return apiRequest(`/v1/research/participants/${publicId}/consent-event`, { method: 'POST', body });
}

export async function excludeParticipantFromMl(publicId) {
  return apiRequest(`/v1/research/participants/${publicId}/exclude-from-ml`, { method: 'POST' });
}

export async function includeParticipantInMl(publicId) {
  return apiRequest(`/v1/research/participants/${publicId}/include-in-ml`, { method: 'POST' });
}
