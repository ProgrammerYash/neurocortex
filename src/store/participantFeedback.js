import { apiRequest } from './apiClient.js';

export async function fetchParticipantModelFeedback() {
  return apiRequest('/v1/participants/me/model-feedback');
}
