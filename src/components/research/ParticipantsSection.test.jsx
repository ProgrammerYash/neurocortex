import { describe, expect, it } from 'vitest';
import { emptyStateMessage } from './ParticipantsSection.jsx';

describe('ParticipantsSection empty states', () => {
  it('uses status-specific wording for suspended', () => {
    expect(emptyStateMessage('suspended', '')).toMatch(/suspended/i);
    expect(emptyStateMessage('suspended', '')).not.toMatch(/enrolled to be suspended/i);
  });

  it('uses search wording when search is present', () => {
    expect(emptyStateMessage('active', 'NC-123')).toMatch(/search/i);
  });
});
