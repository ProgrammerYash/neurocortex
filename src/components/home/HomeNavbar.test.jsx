import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import HomeNavbar from './HomeNavbar.jsx';
import { sectionNav } from '../../content/presentationContent.js';

describe('HomeNavbar', () => {
  it('keeps all section links in order without scroll-slider classes', () => {
    render(
      <MemoryRouter>
        <HomeNavbar />
      </MemoryRouter>,
    );
    expect(document.querySelector('.home-navbar--persistent')).toBeTruthy();
    expect(document.querySelector('.home-navbar-section-scroll')).toBeNull();
    expect(document.querySelector('.home-navbar__sections-scroll')).toBeNull();
    const links = [...screen.getByTestId('home-navbar-section-links').querySelectorAll('a, button')];
    const labels = links.map(node => node.textContent?.trim());
    expect(labels).toEqual(sectionNav.map(item => item.label));
    expect(screen.getByRole('button', { name: /Participant Sign In/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Join the Study/i })).toBeInTheDocument();
  });
});
