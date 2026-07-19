const PAUSE_THRESHOLD_MS = 500;

export function computeRoundMetrics({
  passage,
  position,
  keyEvents,
  backspaces,
  intervals,
  dwells,
  incorrectKeystrokes,
  correctedErrors,
  startPerf,
  endPerf,
  difficulty,
  roundNumber,
}) {
  const durationMs = Math.max(0, Math.round(endPerf - startPerf));
  const durationMin = durationMs / 60000;
  const charsCompleted = position;
  const wpm = durationMin > 0 ? Math.round((charsCompleted / 5) / durationMin) : 0;

  const totalKeys = keyEvents.length;
  const correctKeystrokes = keyEvents.filter((k) => k.correct).length;
  const printableAttempts = correctKeystrokes + incorrectKeystrokes;
  const accuracy = printableAttempts > 0
    ? Math.round((correctKeystrokes / printableAttempts) * 100)
    : 0;
  const errorRate = printableAttempts > 0
    ? Math.round((incorrectKeystrokes / printableAttempts) * 100)
    : 0;
  const uncorrectedErrors = Math.max(0, incorrectKeystrokes - correctedErrors);

  const avgInterval = intervals.length > 0
    ? Math.round(intervals.reduce((a, b) => a + b, 0) / intervals.length)
    : 0;
  const variance = intervals.length > 1
    ? Math.round(intervals.reduce((s, v) => s + Math.pow(v - avgInterval, 2), 0) / intervals.length)
    : 0;
  const avgDwell = dwells.length > 0
    ? Math.round(dwells.reduce((a, b) => a + b, 0) / dwells.length)
    : 0;
  const pauseCount = intervals.filter((i) => i > PAUSE_THRESHOLD_MS).length;
  const pauseFrequency = intervals.length > 0 ? Number((pauseCount / intervals.length).toFixed(2)) : 0;
  const burstLength = keyEvents.filter((k) => k.correct).length > 0
    ? Math.max(1, Math.round(correctKeystrokes / Math.max(1, pauseCount + 1)))
    : 0;
  const errCorrectionRate = totalKeys > 0 ? Math.round((backspaces / totalKeys) * 100) : 0;

  return {
    round: roundNumber,
    difficulty,
    passageLength: passage.length,
    charsCompleted,
    completed: position >= passage.length,
    wpm,
    accuracy,
    errorRate,
    errors: incorrectKeystrokes,
    incorrectKeystrokes,
    correctKeystrokes,
    printableAttempts,
    correctedErrors,
    uncorrectedErrors,
    backspaces,
    totalKeys,
    avgInterval,
    variance,
    avgDwell,
    burstLength,
    pauseFrequency,
    pauseCount,
    durationMs,
    errCorrectionRate,
  };
}

export function aggregateTypingResults(roundMetrics) {
  const rounds = roundMetrics.filter(Boolean);
  if (!rounds.length) {
    return {
      wpm: 0,
      errorRate: 0,
      accuracy: 0,
      backspaces: 0,
      avgInterval: 0,
      variance: 0,
      avgDwell: 0,
      burstLength: 0,
      pauseFrequency: 0,
      pauseCount: 0,
      totalKeys: 0,
      printableAttempts: 0,
      errCorrectionRate: 0,
      durationMs: 0,
      rounds: [],
      rhythmScore: 0,
      timestamp: Date.now(),
    };
  }

  const wpm = Math.round(rounds.reduce((s, r) => s + r.wpm, 0) / rounds.length);
  const backspaces = rounds.reduce((s, r) => s + r.backspaces, 0);
  const totalKeys = rounds.reduce((s, r) => s + r.totalKeys, 0);
  const correctKeystrokes = rounds.reduce((s, r) => s + r.correctKeystrokes, 0);
  const incorrectKeystrokes = rounds.reduce((s, r) => s + r.incorrectKeystrokes, 0);
  const printableAttempts = correctKeystrokes + incorrectKeystrokes;
  const accuracy = printableAttempts > 0
    ? Math.round((correctKeystrokes / printableAttempts) * 100)
    : 0;
  const errorRate = printableAttempts > 0
    ? Math.round((incorrectKeystrokes / printableAttempts) * 100)
    : 0;
  const durationMs = rounds.reduce((s, r) => s + r.durationMs, 0);
  const pauseCount = rounds.reduce((s, r) => s + r.pauseCount, 0);

  const allIntervals = rounds.flatMap((r) => r._intervals || []);
  const allDwells = rounds.flatMap((r) => r._dwells || []);
  const avgInterval = allIntervals.length > 0
    ? Math.round(allIntervals.reduce((a, b) => a + b, 0) / allIntervals.length)
    : Math.round(rounds.reduce((s, r) => s + r.avgInterval, 0) / rounds.length);
  const variance = allIntervals.length > 1
    ? Math.round(allIntervals.reduce((s, v) => s + Math.pow(v - avgInterval, 2), 0) / allIntervals.length)
    : Math.round(rounds.reduce((s, r) => s + r.variance, 0) / rounds.length);
  const avgDwell = allDwells.length > 0
    ? Math.round(allDwells.reduce((a, b) => a + b, 0) / allDwells.length)
    : Math.round(rounds.reduce((s, r) => s + r.avgDwell, 0) / rounds.length);
  const pauseFrequency = allIntervals.length > 0
    ? Number((pauseCount / allIntervals.length).toFixed(2))
    : Number((rounds.reduce((s, r) => s + r.pauseFrequency, 0) / rounds.length).toFixed(2));
  const burstLength = Math.round(rounds.reduce((s, r) => s + r.burstLength, 0) / rounds.length);
  const errCorrectionRate = totalKeys > 0 ? Math.round((backspaces / totalKeys) * 100) : 0;
  const totalErrors = rounds.reduce((s, r) => s + r.errors, 0);
  const rhythmScore = Math.max(0, Math.min(100, Math.round(100 - Math.min(variance / 5, 100))));

  const publicRounds = rounds.map(({ _intervals, _dwells, ...rest }) => rest);

  return {
    wpm,
    errorRate,
    accuracy,
    backspaces,
    avgInterval,
    variance,
    avgDwell,
    burstLength,
    pauseFrequency,
    pauseCount,
    totalKeys,
    printableAttempts,
    errCorrectionRate,
    durationMs,
    totalErrors,
    correctedErrors: rounds.reduce((s, r) => s + r.correctedErrors, 0),
    uncorrectedErrors: rounds.reduce((s, r) => s + r.uncorrectedErrors, 0),
    correctKeystrokes,
    incorrectKeystrokes,
    rounds: publicRounds,
    roundCount: rounds.length,
    rhythmScore,
    timestamp: Date.now(),
  };
}
