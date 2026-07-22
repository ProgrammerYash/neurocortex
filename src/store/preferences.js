import { apiRequest } from './apiClient.js';

export async function updateParticipantStudyFrequency(studyFrequency) {
  return apiRequest('/v1/participants/me/preferences', {
    method: 'PATCH',
    body: { study_frequency: studyFrequency },
  });
}
