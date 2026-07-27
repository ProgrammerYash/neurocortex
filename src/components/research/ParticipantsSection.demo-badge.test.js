import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const participantsSection = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), 'ParticipantsSection.jsx'),
  'utf8',
);
const dashboard = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../dashboard/Dashboard.jsx'),
  'utf8',
);

describe('Phase 5G hidden demo badges', () => {
  it('researcher participant table does not render gold Demo badge markup', () => {
    expect(participantsSection).not.toMatch(/>\s*Demo\s*</);
    expect(participantsSection).not.toContain('Golden Vault demo override active');
  });

  it('participant dashboard does not render Demo account badge', () => {
    expect(dashboard).not.toContain('Demo account');
  });
});
