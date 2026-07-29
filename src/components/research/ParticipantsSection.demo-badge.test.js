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
  it('researcher participant table renders Synthetic Demo badge markup', () => {
    expect(participantsSection).toContain('Synthetic Demo');
    expect(participantsSection).toContain('participantType: participantTypeFilter');
    expect(participantsSection).toContain('Includes synthetic demo participants.');
  });

  it('participant dashboard does not render Demo account badge', () => {
    expect(dashboard).not.toContain('Demo account');
  });
});
