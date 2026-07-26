import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import RouteFocusMain from './RouteFocusMain.jsx';
import { ROUTES } from './routePaths.js';

describe('RouteFocusMain', () => {
  it('focuses the main landmark on home without targeting the hero title', async () => {
    render(
      <MemoryRouter initialEntries={[ROUTES.home]}>
        <Routes>
          <Route
            path={ROUTES.home}
            element={(
              <RouteFocusMain>
                <div>
                  <h1 id="home-title">NeuroCortex: Science Fair Project</h1>
                </div>
              </RouteFocusMain>
            )}
          />
        </Routes>
      </MemoryRouter>,
    );
    const main = screen.getByTestId('route-focus-main');
    await waitFor(() => {
      expect(document.activeElement).toBe(main);
    });
    expect(document.activeElement).not.toHaveAttribute('id', 'home-title');
  });
});
