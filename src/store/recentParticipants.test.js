import { describe, expect, it, beforeEach, vi } from 'vitest';
import {
  addRecentParticipant,
  getRecentParticipants,
  removeRecentParticipant,
  replaceRecentParticipants,
} from './recentParticipants.js';

describe('recentParticipants storage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('safely parses and returns valid entries', () => {
    addRecentParticipant({ id: 'NC-ABC123', grade: '8', ageRange: '13-14', role: 'participant' });
    expect(getRecentParticipants()).toHaveLength(1);
    expect(getRecentParticipants()[0].id).toBe('NC-ABC123');
  });

  it('does not crash on malformed localStorage', () => {
    localStorage.setItem('nc3_recent_participants', '{not-json');
    expect(getRecentParticipants()).toEqual([]);
  });

  it('deduplicates entries', () => {
    replaceRecentParticipants([
      { id: 'NC-ONE', grade: '7' },
      { id: 'NC-ONE', grade: '8' },
      { id: 'NC-TWO', grade: '9' },
    ]);
    expect(getRecentParticipants().map(p => p.id)).toEqual(['NC-ONE', 'NC-TWO']);
  });

  it('removes one participant without clearing others', () => {
    replaceRecentParticipants([
      { id: 'NC-ONE', grade: '7' },
      { id: 'NC-TWO', grade: '8' },
    ]);
    removeRecentParticipant('NC-ONE');
    expect(getRecentParticipants().map(p => p.id)).toEqual(['NC-TWO']);
  });
});
