import { useCallback, useEffect, useId, useState } from 'react';
import { sectionNav } from '../../content/presentationContent.js';

export default function HomeNavbar({ onJoinStudy, onSignIn }) {
  const [open, setOpen] = useState(false);
  const menuId = useId();

  const closeMenu = useCallback(() => setOpen(false), []);

  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = event => {
      if (event.key === 'Escape') closeMenu();
    };
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [open, closeMenu]);

  const navLink = (id, label) => (
    <a key={id} className="home-navbar__link" href={`#${id}`} onClick={closeMenu}>
      {label}
    </a>
  );

  return (
    <>
      <header className="home-navbar">
        <div className="home-navbar__inner">
          <button type="button" className="home-navbar__brand" onClick={() => document.getElementById('home')?.scrollIntoView({ behavior: 'smooth' })}>
            NeuroCortex
          </button>
          <nav className="home-navbar__links" aria-label="Primary">
            {sectionNav.map(item => navLink(item.id, item.label))}
          </nav>
          <div className="home-navbar__actions">
            <button type="button" className="home-btn" onClick={onSignIn}>Participant Sign In</button>
            <button type="button" className="home-btn home-btn--primary" onClick={onJoinStudy}>Join the Study</button>
          </div>
          <button
            type="button"
            className="home-navbar__menu-btn"
            aria-expanded={open}
            aria-controls={menuId}
            aria-label={open ? 'Close menu' : 'Open menu'}
            onClick={() => setOpen(value => !value)}
          >
            {open ? '✕' : '☰'}
          </button>
        </div>
      </header>
      {open && (
        <nav id={menuId} className="home-mobile-menu" aria-label="Mobile">
          {sectionNav.map(item => navLink(item.id, item.label))}
          <button type="button" onClick={() => { closeMenu(); onSignIn(); }}>Participant Sign In</button>
          <button type="button" className="home-btn home-btn--primary" onClick={() => { closeMenu(); onJoinStudy(); }}>Join the Study</button>
        </nav>
      )}
    </>
  );
}
