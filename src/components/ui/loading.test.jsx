import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import AppPageLoader from './AppPageLoader.jsx';
import InlineLoadingIndicator from './InlineLoadingIndicator.jsx';
import ButtonSpinner from './ButtonSpinner.jsx';

describe('loading indicators', () => {
  it('renders AppPageLoader with status role', () => {
    render(<AppPageLoader label="Loading app" />);
    expect(screen.getByTestId('app-page-loader')).toHaveAttribute('role', 'status');
    expect(screen.getByText('Loading app')).toBeInTheDocument();
  });

  it('renders inline and button spinners', () => {
    render(
      <>
        <InlineLoadingIndicator />
        <ButtonSpinner />
      </>,
    );
    expect(screen.getAllByTestId('inline-loading-indicator').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByTestId('button-spinner')).toBeInTheDocument();
  });
});
