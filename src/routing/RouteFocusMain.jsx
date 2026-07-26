import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { ROUTES } from './routePaths.js';

export default function RouteFocusMain({ children }) {
  const location = useLocation();
  const mainRef = useRef(null);

  useEffect(() => {
    const node = mainRef.current;
    if (!node) return;

    const isPublicHome = location.pathname === ROUTES.home;
    if (isPublicHome) {
      node.setAttribute('tabindex', '-1');
      node.focus({ preventScroll: true });
      return;
    }

    const focusTarget = node.querySelector('[data-route-focus]');
    if (focusTarget && typeof focusTarget.focus === 'function') {
      focusTarget.setAttribute('tabindex', '-1');
      focusTarget.focus({ preventScroll: true });
      return;
    }

    node.setAttribute('tabindex', '-1');
    node.focus({ preventScroll: true });
  }, [location.pathname]);

  return (
    <main ref={mainRef} id="app-main" data-testid="route-focus-main">
      {children}
    </main>
  );
}
