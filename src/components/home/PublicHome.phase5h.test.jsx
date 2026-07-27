import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import PublicHome from './PublicHome.jsx';

describe('PublicHome Phase 5H', () => {
  it('renders Explore the Research in a hero button', () => {
    render(
      <MemoryRouter>
        <PublicHome />
      </MemoryRouter>,
    );
    const btn = screen.getByRole('button', { name: /Explore the Research/i });
    expect(btn).toBeInTheDocument();
    expect(btn.className).toMatch(/home-btn/);
  });

  it('renders bottom Researcher Access and Back to Top without underline class conflict', () => {
    render(
      <MemoryRouter>
        <PublicHome />
      </MemoryRouter>,
    );
    const cta = document.querySelector('.home-cta');
    expect(cta).toBeTruthy();
    expect(within(cta).getByRole('button', { name: /Researcher Access/i })).toBeInTheDocument();
    const back = within(cta).getByRole('link', { name: /Back to Top/i });
    expect(back.className).toMatch(/home-btn--top/);
  });
});
