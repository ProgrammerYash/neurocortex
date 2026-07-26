import { useCallback, useEffect, useId, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { sectionNav } from '../../content/presentationContent.js';
import { ROUTES } from '../../routing/routePaths.js';

function NavActions({ onNavigate, className = '' }) {
  const navigate = useNavigate();
  return (
    <div className={`home-navbar__actions ${className}`.trim()} data-testid={className.includes('mobile') ? 'home-navbar-actions-mobile' : 'home-navbar-actions-desktop'}>
      <button type="button" className="home-btn" onClick={() => { onNavigate?.(); navigate(ROUTES.participantSignIn); }}>
        Participant Sign In
      </button>
      <button type="button" className="home-btn home-btn--primary" onClick={() => { onNavigate?.(); navigate(ROUTES.join); }}>
        Join the Study
      </button>
      <button type="button" className="home-btn" onClick={() => { onNavigate?.(); navigate(ROUTES.researcherSignIn); }}>
        Researcher Access
      </button>
    </div>
  );
}

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
      <header className="home-navbar home-navbar--persistent">
        <div className="home-navbar__shell">
          <div className="home-navbar__row home-navbar-top-row home-navbar__row--top" data-testid="home-navbar-top-row">
            <button type="button" className="home-navbar__brand" onClick={goHome}>
              NeuroCortex
            </button>
            <NavActions className="home-navbar__actions--desktop" />
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
          <div
            className="home-navbar__row home-navbar__row--actions"
            data-testid="home-navbar-actions-row"
          >
            <NavActions onNavigate={closeMenu} className="home-navbar__actions--mobile" />
          </div>
          <nav
            className="home-navbar__row home-navbar-section-row home-navbar__row--sections"
            aria-label="Primary"
            data-testid="home-navbar-section-row"
          >
            <div className="home-navbar__sections-inner">
              <div className="home-navbar__section-links" data-testid="home-navbar-section-links">
                {sectionNav.map(item => navLink(item))}
              </div>
            </div>
          </nav>
        </div>
      </header>
      {open && (
        <nav id={menuId} className="home-mobile-menu" aria-label="Mobile">
          {sectionNav.map(item => navLink(item))}
        </nav>
      )}
    </>
  );
}
