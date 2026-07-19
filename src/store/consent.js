import { apiRequest } from './apiClient.js';

export async function fetchMyConsentStatus() {
  return apiRequest('/v1/participants/me/consent-status');
}

export async function submitMyConsent(body) {
  return apiRequest('/v1/participants/me/consent', { method: 'POST', body });
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
