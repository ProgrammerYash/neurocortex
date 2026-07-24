import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import PublicHome from './PublicHome.jsx';
import { HeroBrainVisual, BRAIN_ANIMATED_SRC, BRAIN_STATIC_SRC } from './HeroBrainVisual.jsx';
import { sectionNav } from '../../content/presentationContent.js';

function renderHome() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="*" element={<PublicHome />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('HeroBrainVisual', () => {
  afterEach(() => cleanup());

  it('renders the local animated transparent WebP by default', () => {
    render(<HeroBrainVisual />);
    const image = document.querySelector('.home-hero-brain-visual__image');
    expect(image).toBeTruthy();
    expect(image).toHaveAttribute('src', BRAIN_ANIMATED_SRC);
    expect(image).toHaveAttribute('alt', '');
    expect(image).toHaveAttribute('aria-hidden', 'true');
    expect(image).toHaveAttribute('draggable', 'false');
    expect(document.querySelector('.home-hero-brain-visual')).toBeTruthy();
    expect(document.querySelector('canvas')).toBeFalsy();
  });

  it('uses the static transparent WebP when reduced motion is enabled', () => {
    vi.stubGlobal('matchMedia', vi.fn(() => ({
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })));
    render(<HeroBrainVisual />);
    const image = document.querySelector('.home-hero-brain-visual__image');
    expect(image).toHaveAttribute('src', BRAIN_STATIC_SRC);
    vi.unstubAllGlobals();
  });

  it('does not reference remote animation URLs', () => {
    render(<HeroBrainVisual />);
    expect(document.body.innerHTML).not.toContain('pinimg.com');
    expect(document.body.innerHTML).not.toContain('beehiiv.com');
    expect(document.body.innerHTML).not.toContain('source-rotating-brain.gif');
  });
});

describe('PublicHome brain and navbar', () => {
  afterEach(() => cleanup());

  it('renders the transparent brain image without 3D canvas', () => {
    renderHome();
    expect(document.querySelector('.home-hero-brain-visual__image')).toBeTruthy();
    expect(document.querySelector('.home-hero-brain-3d')).toBeFalsy();
    expect(document.querySelector('canvas')).toBeFalsy();
    expect(document.querySelector('.home-hero-brain-profile')).toBeFalsy();
  });

  it('keeps the two-row navbar and ordered section links', () => {
    renderHome();
    expect(screen.getByTestId('home-navbar-top-row')).toBeInTheDocument();
    expect(screen.getByTestId('home-navbar-section-row')).toBeInTheDocument();
    const labels = [...screen.getByTestId('home-navbar-section-links').querySelectorAll('a')]
      .map(link => link.textContent);
    expect(labels).toEqual(sectionNav.map(item => item.label));
    expect(labels).toHaveLength(11);
  });

  it('still renders hero controls if the brain image fails to load', () => {
    renderHome();
    const image = document.querySelector('.home-hero-brain-visual__image');
    image?.dispatchEvent(new Event('error'));
    expect(screen.getByRole('button', { name: 'Explore the Research' })).toBeInTheDocument();
  });
});
