import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';

export default function RouteFocusMain({ children }) {
  const location = useLocation();
  const mainRef = useRef(null);

  useEffect(() => {
    const node = mainRef.current;
    if (!node) return;
    const heading = node.querySelector('h1, [data-route-focus]');
    if (heading && typeof heading.focus === 'function') {
      heading.setAttribute('tabindex', '-1');
      heading.focus({ preventScroll: true });
    }
  }, [location.pathname]);

  return (
    <main ref={mainRef} id="app-main">
      {children}
    </main>
  );
}
