export const ROUTES = {
  home: '/',
  join: '/join',
  participantSignIn: '/participant/sign-in',
  participantChangePin: '/participant/change-pin',
  participantConsent: '/participant/consent',
  participantDashboard: '/participant/dashboard',
  participantInbox: '/participant/inbox',
  participantNeuroverse: '/participant/neuroverse',
  participantPet: '/participant/pet',
  participantAchievements: '/participant/achievements',
  reaction: '/participant/session/reaction-time',
  typing: '/participant/session/typing',
  memory: '/participant/session/memory',
  attention: '/participant/session/attention',
  survey: '/participant/session/daily-survey',
  nasaTlx: '/participant/session/nasa-tlx',
  researcherSignIn: '/researcher/sign-in',
  researcherDashboard: '/researcher/dashboard',
};

export const MODULE_SCREEN_TO_PATH = {
  dashboard: ROUTES.participantDashboard,
  inbox: ROUTES.participantInbox,
  reaction: ROUTES.reaction,
  typing: ROUTES.typing,
  memory: ROUTES.memory,
  attention: ROUTES.attention,
  survey: ROUTES.survey,
  nasatlx: ROUTES.nasaTlx,
  pet: ROUTES.participantPet,
  achievements: ROUTES.participantAchievements,
  neuroverse: ROUTES.participantNeuroverse,
};

export function isParticipantAppPath(pathname) {
  return pathname.startsWith('/participant');
}

export function isResearcherAppPath(pathname) {
  return pathname.startsWith('/researcher');
}

export function isProtectedAppPath(pathname) {
  return isParticipantAppPath(pathname) || isResearcherAppPath(pathname);
}
