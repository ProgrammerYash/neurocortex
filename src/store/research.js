import { apiRequest } from './apiClient.js';
import { getToken } from './auth.js';

function useLocalStore() {
  return import.meta.env.VITE_USE_LOCAL_STORE === 'true';
}

export function getTokenRole() {
  if (useLocalStore()) return null;
  const token = getToken();
  if (!token) return null;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.role ?? null;
  } catch {
    return null;
  }
}

export function isResearcherAuthed() {
  return getTokenRole() === 'researcher';
}

export async function fetchResearchParticipants() {
  return apiRequest('/v1/research/participants');
}

export async function fetchResearchSessions() {
  return apiRequest('/v1/research/sessions');
}

export async function fetchResearchStats() {
  return apiRequest('/v1/research/stats');
}

export async function fetchDashboardSummary() {
  return apiRequest('/v1/research/dashboard/summary');
}

export async function fetchDashboardParticipants({
  limit = 20,
  offset = 0,
  search = '',
  sort = 'joined',
  direction = 'desc',
  status = 'all_current',
} = {}) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
    sort,
    direction,
    status,
  });
  if (search.trim()) params.set('search', search.trim());
  return apiRequest(`/v1/research/dashboard/participants?${params.toString()}`);
}

export async function fetchDashboardParticipantDetail(publicId) {
  return apiRequest(`/v1/research/dashboard/participants/${encodeURIComponent(publicId)}`);
}

export async function fetchParticipantAccountActions(publicId) {
  return apiRequest(`/v1/research/dashboard/participants/${encodeURIComponent(publicId)}/account-actions`);
}

export async function suspendParticipantAccount(publicId, { duration, reason }) {
  return apiRequest(`/v1/research/dashboard/participants/${encodeURIComponent(publicId)}/suspend`, {
    method: 'POST',
    body: { duration, reason },
  });
}

export async function unsuspendParticipantAccount(publicId, { reason }) {
  return apiRequest(`/v1/research/dashboard/participants/${encodeURIComponent(publicId)}/unsuspend`, {
    method: 'POST',
    body: { reason },
  });
}

export async function resetParticipantPin(publicId) {
  return apiRequest(`/v1/research/dashboard/participants/${encodeURIComponent(publicId)}/reset-pin`, {
    method: 'POST',
    body: {},
  });
}

export async function disableParticipantAccount(publicId, { reason }) {
  return apiRequest(`/v1/research/dashboard/participants/${encodeURIComponent(publicId)}/disable`, {
    method: 'POST',
    body: { reason },
  });
}

export async function enableParticipantAccount(publicId, { reason }) {
  return apiRequest(`/v1/research/dashboard/participants/${encodeURIComponent(publicId)}/enable`, {
    method: 'POST',
    body: { reason },
  });
}

export async function removeParticipantAccount(publicId, { reason, confirmationPublicId }) {
  return apiRequest(`/v1/research/dashboard/participants/${encodeURIComponent(publicId)}/remove-account`, {
    method: 'POST',
    body: { reason, confirmation_public_id: confirmationPublicId },
  });
}

export async function buildResearchDataset(name, datasetMode = 'strict') {
  return apiRequest('/v1/research/datasets/build', {
    method: 'POST',
    body: name ? { name, dataset_mode: datasetMode } : { dataset_mode: datasetMode },
  });
}

export async function fetchResearchDatasets() {
  return apiRequest('/v1/research/datasets');
}

export async function fetchResearchDataset(datasetId) {
  return apiRequest(`/v1/research/datasets/${datasetId}`);
}

export async function fetchResearchDatasetSummary(datasetId) {
  return apiRequest(`/v1/research/datasets/${datasetId}/summary`);
}

export async function fetchResearchDatasetRows(datasetId, { limit = 100, offset = 0 } = {}) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  return apiRequest(`/v1/research/datasets/${datasetId}/rows?${params.toString()}`);
}

export async function labelResearchDataset(datasetId) {
  return apiRequest(`/v1/research/datasets/${datasetId}/label`, { method: 'POST' });
}

export async function fetchResearchDatasetStatistics(datasetId) {
  return apiRequest(`/v1/research/datasets/${datasetId}/statistics`);
}

export async function fetchResearchDatasetCorrelations(datasetId) {
  return apiRequest(`/v1/research/datasets/${datasetId}/correlations`);
}

export async function fetchResearchDatasetQuality(datasetId) {
  return apiRequest(`/v1/research/datasets/${datasetId}/quality`);
}

export async function fetchResearchDatasetLabels(datasetId) {
  return apiRequest(`/v1/research/datasets/${datasetId}/labels`);
}

export async function trainResearchModel({ datasetId, targetLabel = 'burnout_next_day', modelType = 'lightgbm' }) {
  return apiRequest('/v1/research/models/train', {
    method: 'POST',
    body: {
      dataset_id: datasetId,
      target_label: targetLabel,
      model_type: modelType,
    },
  });
}

export async function fetchResearchModels() {
  return apiRequest('/v1/research/models');
}

export async function fetchResearchModel(modelId) {
  return apiRequest(`/v1/research/models/${modelId}`);
}

export async function predictParticipant(modelId, { participantId, sessionDate }) {
  return apiRequest(`/v1/research/models/${modelId}/predict`, {
    method: 'POST',
    body: {
      participant_id: participantId,
      session_date: sessionDate,
    },
  });
}

export async function batchPredict(modelId) {
  return apiRequest(`/v1/research/models/${modelId}/batch-predict`, { method: 'POST' });
}

export async function getPredictions() {
  return apiRequest('/v1/research/predictions');
}

export async function getParticipantPredictions(participantId) {
  return apiRequest(`/v1/research/predictions/${participantId}`);
}

export async function explainPrediction(predictionId) {
  return apiRequest(`/v1/research/predictions/${predictionId}/explain`, { method: 'POST' });
}

export async function getExplanation(predictionId) {
  return apiRequest(`/v1/research/predictions/${predictionId}/explanation`);
}

export async function getFeatureImportance(modelId) {
  return apiRequest(`/v1/research/models/${modelId}/feature-importance`);
}

export async function compareModels() {
  return apiRequest('/v1/research/models/compare');
}

export async function fetchStudyConfig() {
  return apiRequest('/v1/research/study-config');
}

export async function fetchStudyProcedure() {
  return apiRequest('/v1/research/study-procedure');
}

export async function fetchDataQualityDashboard() {
  return apiRequest('/v1/research/data-quality/dashboard');
}

export async function fetchFlaggedSessions() {
  return apiRequest('/v1/research/data-quality/flagged-sessions');
}

export async function reviewDataQualityFlag(flagId, reviewStatus) {
  return apiRequest(`/v1/research/data-quality/flags/${flagId}/review`, {
    method: 'POST',
    body: { review_status: reviewStatus },
  });
}
