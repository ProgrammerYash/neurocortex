import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';
import HomeNavbar from './HomeNavbar.jsx';
import { sectionNav } from '../../content/presentationContent.js';

describe('HomeNavbar', () => {
  afterEach(() => cleanup());

  it('keeps section links in order and exposes Researcher Access in action row', () => {
    render(
      <MemoryRouter>
        <HomeNavbar />
      </MemoryRouter>,
    );
    const links = [...screen.getByTestId('home-navbar-section-links').querySelectorAll('a, button')];
    const labels = links.map(node => node.textContent?.trim());
    expect(labels).toEqual(sectionNav.map(item => item.label));
    expect(screen.getAllByRole('button', { name: /Researcher Access/i }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole('button', { name: /Participant Sign In/i }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole('button', { name: /Join the Study/i }).length).toBeGreaterThan(0);
  });

  it('mobile menu lists sections only (no sign-in or join actions)', () => {
    render(
      <MemoryRouter>
        <HomeNavbar />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Open menu' }));
    const mobile = screen.getByRole('navigation', { name: 'Mobile' });
    expect(mobile.querySelector('button')).toBeNull();
    expect(mobile.textContent).not.toMatch(/Participant Sign In/);
    expect(mobile.textContent).not.toMatch(/Join the Study/);
    expect(mobile.textContent).not.toMatch(/Researcher Access/);
  });
});
