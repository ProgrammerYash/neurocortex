import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import PublicHome from './PublicHome.jsx';
import { allRequiredVerbatimStrings } from '../../content/presentationContent.js';

function renderHome(overrides = {}) {
  const onJoinStudy = vi.fn();
  const onSignIn = vi.fn();
  const onResearcherAccess = vi.fn();
  render(
    <PublicHome
      onJoinStudy={onJoinStudy}
      onSignIn={onSignIn}
      onResearcherAccess={onResearcherAccess}
      {...overrides}
    />,
  );
  return { onJoinStudy, onSignIn, onResearcherAccess };
}

describe('PublicHome presentation content', () => {
  afterEach(() => {
    cleanup();
  });

  it('renders every required verbatim presentation string', () => {
    renderHome();
    allRequiredVerbatimStrings().forEach(text => {
      const matches = screen.getAllByText((content, node) => {
        const normalized = node?.textContent?.replace(/\s+/g, ' ').trim();
        return normalized === text || normalized?.includes(text);
      });
      expect(matches.length, `Missing: ${text.slice(0, 60)}…`).toBeGreaterThan(0);
    });
  });

  it('repeats closing title-slide credits near the bottom', () => {
    renderHome();
    expect(screen.getAllByText('Science Fair Project Presentation').length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText('By Yash Gupta').length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText('Jose Marti STEM Academy').length).toBeGreaterThanOrEqual(2);
  });

  it('omits forbidden placeholder and branding text', () => {
    renderHome();
    expect(screen.queryByText('More Info')).not.toBeInTheDocument();
    expect(screen.queryByText(/lorem ipsum/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/ISEF Longitudinal Research Platform/i)).not.toBeInTheDocument();
  });

  it('shows primary call-to-action buttons', () => {
    renderHome();
    expect(screen.getAllByRole('button', { name: 'Join the Study' }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole('button', { name: 'Participant Sign In' }).length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: 'Explore the Research' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Back to Top' })).toBeInTheDocument();
  });

  it('routes Join the Study and Participant Sign In to existing flows', () => {
    const { onJoinStudy, onSignIn } = renderHome();
    fireEvent.click(screen.getAllByRole('button', { name: 'Join the Study' })[0]);
    fireEvent.click(screen.getAllByRole('button', { name: 'Participant Sign In' })[0]);
    expect(onJoinStudy).toHaveBeenCalled();
    expect(onSignIn).toHaveBeenCalled();
  });

  it('opens and closes the mobile menu', () => {
    renderHome();
    fireEvent.click(screen.getByRole('button', { name: 'Open menu' }));
    expect(screen.getByRole('button', { name: 'Close menu' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('navigation', { name: 'Mobile' }).querySelector('a[href="#home"]'));
    expect(screen.queryByRole('button', { name: 'Close menu' })).not.toBeInTheDocument();
  });

  it('shows four future-work numbers only inside numbered cards', () => {
    renderHome();
    ['01', '02', '03', '04'].forEach(number => {
      expect(screen.getByText(number)).toBeInTheDocument();
    });
  });
});
