// Original NeuroCortex passages — age-appropriate, not copyrighted material.
// Grouped by adaptive difficulty (easy → medium → hard).

export const TYPING_PASSAGES_BY_DIFFICULTY = {
  easy: [
    'The sun warms the quiet park path.',
    'Birds sing softly in the morning trees.',
    'Students pack their bags after class ends.',
    'A cool breeze moves through the open window.',
  ],
  medium: [
    'Healthy sleep helps your brain store new memories from the school day.',
    'Taking short breaks during study time can improve focus and reduce stress.',
    'Practice builds skill, but rest gives your mind time to recover and grow.',
    'Team projects teach students how to plan tasks and communicate clearly.',
  ],
  hard: [
    'Neuroscience research shows that consistent routines support attention, mood, and learning over time.',
    'When tasks feel overwhelming, breaking work into smaller steps can reduce mental fatigue and improve accuracy.',
    'Scientists measure typing rhythm because small changes in speed, pauses, and corrections may reflect cognitive load.',
    'Balanced study habits—sleep, movement, and focused practice—help students perform well without burning out.',
  ],
};

export const DIFFICULTY_ORDER = ['easy', 'medium', 'hard'];

/** @deprecated Use TYPING_PASSAGES_BY_DIFFICULTY — kept for any legacy imports */
export const TYPING_PASSAGES = Object.values(TYPING_PASSAGES_BY_DIFFICULTY).flat();

export function pickPassage(difficulty, usedTexts = []) {
  const pool = (TYPING_PASSAGES_BY_DIFFICULTY[difficulty] || TYPING_PASSAGES_BY_DIFFICULTY.easy)
    .filter((text) => !usedTexts.includes(text));
  const choices = pool.length > 0 ? pool : TYPING_PASSAGES_BY_DIFFICULTY[difficulty] || TYPING_PASSAGES_BY_DIFFICULTY.easy;
  return choices[Math.floor(Math.random() * choices.length)];
}

export function adaptDifficulty(currentDifficulty, accuracy, wpm) {
  const idx = Math.max(0, DIFFICULTY_ORDER.indexOf(currentDifficulty));
  const speedStrong = wpm >= (currentDifficulty === 'easy' ? 28 : currentDifficulty === 'medium' ? 38 : 45);

  if (accuracy >= 95 && speedStrong) {
    return DIFFICULTY_ORDER[Math.min(idx + 1, DIFFICULTY_ORDER.length - 1)];
  }
  if (accuracy < 85) {
    return DIFFICULTY_ORDER[Math.max(idx - 1, 0)];
  }
  return currentDifficulty;
}

export function roundTimeLimitSeconds(difficulty) {
  if (difficulty === 'easy') return 75;
  if (difficulty === 'medium') return 85;
  return 95;
}
