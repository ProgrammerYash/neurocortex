import { Navigate, useLocation } from 'react-router-dom';
import { ROUTES, isParticipantAppPath, isResearcherAppPath } from './routePaths.js';

function needsStudySchedule(user) {
  return user?.studyFrequency == null || user?.studyFrequency === '';
}

export function RequireParticipant({
  user,
  children,
  allowPinChangeOnly = false,
  allowConsentOnly = false,
  allowScheduleOnly = false,
}) {
  const location = useLocation();
  if (!user || user.role !== 'participant') {
    return <Navigate to={ROUTES.participantSignIn} state={{ from: location }} replace />;
  }
  const path = location.pathname;
  const needsConsent = user.consentRequired === true || user.consentRecorded === false;

  if (user.mustChangePin && path !== ROUTES.participantChangePin && !allowPinChangeOnly) {
    return <Navigate to={ROUTES.participantChangePin} replace />;
  }
  if (!user.mustChangePin && needsConsent && path !== ROUTES.participantConsent && !allowConsentOnly) {
    return <Navigate to={ROUTES.participantConsent} replace />;
  }
  if (
    !user.mustChangePin
    && !needsConsent
    && needsStudySchedule(user)
    && path !== ROUTES.participantSchedule
    && !allowScheduleOnly
  ) {
    return <Navigate to={ROUTES.participantSchedule} replace />;
  }
  if (!user.mustChangePin && !needsConsent && !needsStudySchedule(user) && path === ROUTES.participantSchedule) {
    return <Navigate to={ROUTES.participantDashboard} replace />;
  }
  if (
    !user.mustChangePin
    && !needsConsent
    && !needsStudySchedule(user)
    && (path === ROUTES.participantChangePin || path === ROUTES.participantConsent)
  ) {
    return <Navigate to={ROUTES.participantDashboard} replace />;
  }
  return children;
}

export function RequireResearcher({ user, children }) {
  const location = useLocation();
  if (!user || user.role !== 'researcher') {
    return <Navigate to={ROUTES.researcherSignIn} state={{ from: location }} replace />;
  }
  if (user.role === 'participant') {
    return <Navigate to={ROUTES.participantDashboard} replace />;
  }
  return children;
}

export function RedirectIfAuthed({ user, children }) {
  if (user?.role === 'participant') {
    if (user.mustChangePin) return <Navigate to={ROUTES.participantChangePin} replace />;
    if (user.consentRequired === true || user.consentRecorded === false) {
      return <Navigate to={ROUTES.participantConsent} replace />;
    }
    if (needsStudySchedule(user)) return <Navigate to={ROUTES.participantSchedule} replace />;
    return <Navigate to={ROUTES.participantDashboard} replace />;
  }
  if (user?.role === 'researcher') {
    return <Navigate to={ROUTES.researcherDashboard} replace />;
  }
  return children;
}

export function BlockCrossRole({ user, expectedRole, children }) {
  if (!user) return children;
  if (expectedRole === 'participant' && user.role === 'researcher') {
    return <Navigate to={ROUTES.researcherDashboard} replace />;
  }
  if (expectedRole === 'researcher' && user.role === 'participant') {
    return <Navigate to={ROUTES.participantDashboard} replace />;
  }
  return children;
}

export function participantPathAllowedWithoutFullSession(pathname) {
  return pathname === ROUTES.participantChangePin
    || pathname === ROUTES.participantConsent
    || pathname === ROUTES.participantSchedule;
}

export function shouldRestoreSession(pathname) {
  if (!isParticipantAppPath(pathname) && !isResearcherAppPath(pathname)) return false;
  if (pathname === ROUTES.participantSignIn || pathname === ROUTES.researcherSignIn) return false;
  return true;
}
