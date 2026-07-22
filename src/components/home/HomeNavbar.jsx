import { useCallback, useEffect, useId, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { sectionNav } from '../../content/presentationContent.js';
import { ROUTES } from '../../routing/routePaths.js';

export default function HomeNavbar() {
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const navigate = useNavigate();
  const location = useLocation();

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

  const goHome = () => {
    closeMenu();
    if (location.pathname !== ROUTES.home) {
      navigate(ROUTES.home);
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const sectionHref = id => {
    if (location.pathname === ROUTES.home) return `#${id}`;
    return `${ROUTES.home}#${id}`;
  };

  const onSectionClick = (event, id) => {
    closeMenu();
    if (location.pathname !== ROUTES.home) return;
    if (id === 'home') {
      event.preventDefault();
      goHome();
    }
  };

  const navLink = item => {
    if (item.id === 'home') {
      return (
        <Link
          key={item.id}
          className="home-navbar__link"
          to={ROUTES.home}
          onClick={event => {
            event.preventDefault();
            goHome();
          }}
        >
          {item.label}
        </Link>
      );
    }
    return (
      <a
        key={item.id}
        className="home-navbar__link"
        href={sectionHref(item.id)}
        onClick={event => onSectionClick(event, item.id)}
      >
        {item.label}
      </a>
    );
  };

  return (
    <>
      <header className="home-navbar">
        <div className="home-navbar__shell">
          <div className="home-navbar__row home-navbar__row--top">
            <button type="button" className="home-navbar__brand" onClick={goHome}>
              NeuroCortex
            </button>
            <div className="home-navbar__actions">
              <button type="button" className="home-btn" onClick={() => navigate(ROUTES.participantSignIn)}>Participant Sign In</button>
              <button type="button" className="home-btn home-btn--primary" onClick={() => navigate(ROUTES.join)}>Join the Study</button>
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
          <nav className="home-navbar__row home-navbar__row--sections" aria-label="Primary">
            <div className="home-navbar__sections-scroll">
              {sectionNav.map(item => navLink(item))}
            </div>
          </nav>
        </div>
      </header>
      {open && (
        <nav id={menuId} className="home-mobile-menu" aria-label="Mobile">
          {sectionNav.map(item => navLink(item))}
          <button type="button" onClick={() => { closeMenu(); navigate(ROUTES.participantSignIn); }}>Participant Sign In</button>
          <button type="button" className="home-btn home-btn--primary" onClick={() => { closeMenu(); navigate(ROUTES.join); }}>Join the Study</button>
        </nav>
      )}
    </>
  );
}
