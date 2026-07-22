import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import PublicHome from './PublicHome.jsx';
import RegisterScreen from '../auth/RegisterScreen.jsx';
import ResearcherSignInScreen from '../auth/ResearcherSignInScreen.jsx';
import { hypothesis, sectionNav, workInProgressLabel, allRequiredVerbatimStrings } from '../../content/presentationContent.js';
import { ROUTES } from '../../routing/routePaths.js';

const purposeLabels = [
  'participant data',
  'digital biomarkers',
  'AI model',
  'user information',
];

function renderAt(path, element) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="*" element={element} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('PublicHome presentation content', () => {
  afterEach(() => {
    cleanup();
  });

  it('renders every required verbatim presentation string', () => {
    renderAt('/', <PublicHome />);
    allRequiredVerbatimStrings().forEach(text => {
      const matches = screen.getAllByText((content, node) => {
        const normalized = node?.textContent?.replace(/\s+/g, ' ').trim();
        return normalized === text || normalized?.includes(text);
      });
      expect(matches.length, `Missing: ${text.slice(0, 60)}…`).toBeGreaterThan(0);
    });
  });

  it('repeats closing title-slide credits near the bottom', () => {
    renderAt('/', <PublicHome />);
    expect(screen.getAllByText('Science Fair Project').length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText('By Yash Gupta').length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText('Jose Marti STEM Academy').length).toBeGreaterThanOrEqual(2);
  });

  it('omits forbidden placeholder and branding text', () => {
    renderAt('/', <PublicHome />);
    expect(screen.queryByText('Science Fair Project Presentation')).not.toBeInTheDocument();
    expect(screen.queryByText('AGENDA')).not.toBeInTheDocument();
    expect(screen.queryByText('2.Computer - HP EliteBook 840 G3')).not.toBeInTheDocument();
    expect(screen.queryByText(/lorem ipsum/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/ISEF Longitudinal Research Platform/i)).not.toBeInTheDocument();
    expect(screen.queryByText('01')).not.toBeInTheDocument();
  });

  it('shows Work in Progress panels and procedure phases', () => {
    renderAt('/', <PublicHome />);
    expect(screen.getAllByText(workInProgressLabel).length).toBeGreaterThanOrEqual(3);
    ['Phase 1', 'Phase 2', 'Phase 3', 'Phase 4', 'Phase 5'].forEach(label => {
      expect(screen.getByText(label)).toBeInTheDocument();
    });
    expect(screen.getByText('CURRENT PHASE')).toBeInTheDocument();
    expect(screen.getByText('2. Computer - HP EliteBook 840 G3')).toBeInTheDocument();
    expect(document.querySelector('.problem-card--wide')).toBeTruthy();
    expect(document.querySelector('.home-hero-brain-profile')).toBeTruthy();
    expect(document.querySelector('.home-hero-brain')).toBeFalsy();
    expect(document.querySelector('.home-purpose-flow')).toBeTruthy();
    purposeLabels.forEach(label => {
      expect(screen.getByText(label)).toBeInTheDocument();
    });
  });

  it('does not render duplicate section eyebrow labels', () => {
    renderAt('/', <PublicHome />);
    expect(screen.queryByClassName?.('home-section__label')).toBeUndefined();
    expect(document.querySelectorAll('.home-section__label')).toHaveLength(0);
  });

  it('renders navbar links in required order', () => {
    renderAt('/', <PublicHome />);
    const sectionRow = document.querySelector('.home-navbar__sections-scroll');
    expect(sectionRow).toBeTruthy();
    const labels = within(sectionRow).getAllByRole('link').map(link => link.textContent);
    expect(labels).toEqual(sectionNav.map(item => item.label));
  });

  it('uses a single full-width Hypothesis card without the old diagram', () => {
    renderAt('/', <PublicHome />);
    expect(screen.getByText(hypothesis.text)).toBeInTheDocument();
    expect(document.querySelectorAll('#hypothesis .home-card--statement')).toHaveLength(1);
    expect(screen.queryByText('digital behavior', { selector: '#hypothesis span' })).not.toBeInTheDocument();
  });

  it('uses a persistent fixed navbar shell', () => {
    renderAt('/', <PublicHome />);
    expect(document.querySelector('.home-navbar--persistent')).toBeTruthy();
    expect(document.querySelector('.home-navbar__sections-inner')).toBeTruthy();
  });

  it('centers all Problem cards', () => {
    renderAt('/', <PublicHome />);
    expect(document.querySelectorAll('.home-problem-grid .home-card--centered-problem')).toHaveLength(5);
  });

  it('opens and closes the mobile menu', () => {
    renderAt('/', <PublicHome />);
    fireEvent.click(screen.getByRole('button', { name: 'Open menu' }));
    expect(screen.getByRole('button', { name: 'Close menu' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('navigation', { name: 'Mobile' }).querySelector('a[href="/"]'));
    expect(screen.queryByRole('button', { name: 'Close menu' })).not.toBeInTheDocument();
  });
});

describe('Researcher access routing UI', () => {
  afterEach(() => cleanup());

  it('shows researcher login without participant registration at /researcher/sign-in', () => {
    renderAt(
      ROUTES.researcherSignIn,
      <ResearcherSignInScreen onLogin={vi.fn()} />,
    );
    expect(screen.getByText('Researcher sign-in')).toBeInTheDocument();
    expect(screen.queryByText('Join the Study')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Participant/i })).not.toBeInTheDocument();
  });

  it('join route shows registration wizard not researcher toggle', () => {
    renderAt(
      ROUTES.join,
      <RegisterScreen onRegister={vi.fn()} showToast={vi.fn()} />,
    );
    expect(screen.getByText(/Join the Study/i)).toBeInTheDocument();
    expect(screen.queryByText('Researcher sign-in')).not.toBeInTheDocument();
  });
});
