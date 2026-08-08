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

describe('Phase 5J synthetic demo visibility', () => {
  it('regular researcher participants section hides synthetic indicators', () => {
    expect(participantsSection).toContain("variant === 'goldenVault'");
    expect(participantsSection).toContain('showSyntheticBadge={isVault}');
    expect(participantsSection).not.toContain('Includes synthetic demo participants.');
  });

  it('golden vault variant keeps participant type filter and badges', () => {
    expect(participantsSection).toContain('PARTICIPANT_TYPE_FILTERS');
    expect(participantsSection).toContain('SyntheticDemoBadge');
  });

  it('participant dashboard does not render Demo account badge', () => {
    expect(dashboard).not.toContain('Demo account');
  });
});
