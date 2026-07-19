import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { T } from '../../constants/tokens.js';
import {
  adaptDifficulty,
  pickPassage,
  roundTimeLimitSeconds,
} from '../../constants/typingPassages.js';
import { aggregateTypingResults, computeRoundMetrics } from '../../utils/typingMetrics.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import LockedScreen from '../ui/LockedScreen.jsx';

const TOTAL_ROUNDS = 3;
const WRONG_FLASH_MS = 180;

function isModifierShortcut(e) {
  return (e.ctrlKey || e.metaKey) && ['v', 'c', 'x', 'a', 'z', 'y'].includes(e.key.toLowerCase());
}

export default function TypingTest({ onComplete, onBack, locked }) {
  const [phase, setPhase] = useState('intro');
  const [roundIndex, setRoundIndex] = useState(0);
  const [difficulty, setDifficulty] = useState('easy');
  const [passage, setPassage] = useState('');
  const [position, setPosition] = useState(0);
  const [timeLeft, setTimeLeft] = useState(0);
  const [wrongFlash, setWrongFlash] = useState(false);
  const [timerActive, setTimerActive] = useState(false);
  const [liveBackspaces, setLiveBackspaces] = useState(0);
  const [roundResults, setRoundResults] = useState([]);
  const [latestRound, setLatestRound] = useState(null);
  const [aggregate, setAggregate] = useState(null);
  const [saveError, setSaveError] = useState('');
  const [saving, setSaving] = useState(false);

  const inputRef = useRef(null);
  const passageRef = useRef(null);
  const currentCharRef = useRef(null);
  const timerRef = useRef(null);
  const wrongFlashRef = useRef(null);
  const completedRef = useRef(false);
  const savingRef = useRef(false);
  const timingStartedRef = useRef(false);
  const startPerfRef = useRef(null);
  const lastKeyPerfRef = useRef(null);
  const positionRef = useRef(0);
  const passageRefText = useRef('');
  const keyEventsRef = useRef([]);
  const intervalsRef = useRef([]);
  const dwellsRef = useRef([]);
  const backspacesRef = useRef(0);
  const incorrectRef = useRef(0);
  const correctedRef = useRef(0);
  const keyDownMapRef = useRef(new Map());
  const usedPassagesRef = useRef([]);
  const roundFinishedRef = useRef(false);

  const clearRoundTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const resetRoundTracking = useCallback(() => {
    positionRef.current = 0;
    setPosition(0);
    timingStartedRef.current = false;
    startPerfRef.current = null;
    lastKeyPerfRef.current = null;
    keyEventsRef.current = [];
    intervalsRef.current = [];
    dwellsRef.current = [];
    backspacesRef.current = 0;
    incorrectRef.current = 0;
    correctedRef.current = 0;
    keyDownMapRef.current = new Map();
    roundFinishedRef.current = false;
    setTimerActive(false);
    setLiveBackspaces(0);
    setWrongFlash(false);
  }, []);

  const focusInput = useCallback(() => {
    setTimeout(() => inputRef.current?.focus(), 80);
  }, []);

  const startRound = useCallback((round, nextDifficulty, usedTexts) => {
    const text = pickPassage(nextDifficulty, usedTexts);
    usedPassagesRef.current = [...usedTexts, text];
    passageRefText.current = text;
    setPassage(text);
    setDifficulty(nextDifficulty);
    setRoundIndex(round);
    setTimeLeft(roundTimeLimitSeconds(nextDifficulty));
    resetRoundTracking();
    setPhase('typing');
    focusInput();
  }, [focusInput, resetRoundTracking]);

  useEffect(() => () => {
    clearRoundTimer();
    if (wrongFlashRef.current) clearTimeout(wrongFlashRef.current);
  }, [clearRoundTimer]);

  useEffect(() => {
    if (phase !== 'typing') return;
    focusInput();
  }, [phase, passage, focusInput]);

  useEffect(() => {
    if (phase !== 'typing' || !currentCharRef.current || !passageRef.current) return;
    currentCharRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' });
  }, [position, phase]);

  const finishRound = useCallback(() => {
    if (roundFinishedRef.current) return;
    roundFinishedRef.current = true;
    clearRoundTimer();
    if (!timingStartedRef.current || startPerfRef.current == null) {
      startPerfRef.current = performance.now();
    }
    const endPerf = performance.now();
    const metrics = computeRoundMetrics({
      passage: passageRefText.current,
      position: positionRef.current,
      keyEvents: keyEventsRef.current,
      backspaces: backspacesRef.current,
      intervals: intervalsRef.current,
      dwells: dwellsRef.current,
      incorrectKeystrokes: incorrectRef.current,
      correctedErrors: correctedRef.current,
      startPerf: startPerfRef.current,
      endPerf,
      difficulty,
      roundNumber: roundIndex + 1,
    });
    metrics._intervals = [...intervalsRef.current];
    metrics._dwells = [...dwellsRef.current];

    setLatestRound(metrics);
    setRoundResults((prev) => {
      const next = [...prev];
      next[roundIndex] = metrics;
      if (roundIndex >= TOTAL_ROUNDS - 1) {
        setAggregate(aggregateTypingResults(next));
        setPhase('final');
      } else {
        setPhase('intermission');
      }
      return next;
    });
  }, [clearRoundTimer, difficulty, roundIndex]);

  const beginTest = useCallback(() => {
    usedPassagesRef.current = [];
    setRoundResults([]);
    setLatestRound(null);
    setAggregate(null);
    setSaveError('');
    completedRef.current = false;
    savingRef.current = false;
    startRound(0, 'easy', []);
  }, [startRound]);

  const continueToNextRound = useCallback(() => {
    const completed = roundResults.filter(Boolean);
    const avgAccuracy = completed.length
      ? Math.round(completed.reduce((s, r) => s + r.accuracy, 0) / completed.length)
      : latestRound?.accuracy ?? 90;
    const avgWpm = completed.length
      ? Math.round(completed.reduce((s, r) => s + r.wpm, 0) / completed.length)
      : latestRound?.wpm ?? 30;
    const baseDifficulty = latestRound?.difficulty ?? difficulty;
    const nextDifficulty = adaptDifficulty(baseDifficulty, avgAccuracy, avgWpm);
    startRound(roundIndex + 1, nextDifficulty, usedPassagesRef.current);
  }, [difficulty, latestRound, roundIndex, roundResults, startRound]);

  const startTimingIfNeeded = useCallback((now) => {
    if (timingStartedRef.current) return;
    timingStartedRef.current = true;
    startPerfRef.current = now;
    lastKeyPerfRef.current = now;
    setTimerActive(true);
    const limit = roundTimeLimitSeconds(difficulty);
    setTimeLeft(limit);
    timerRef.current = setInterval(() => {
      setTimeLeft((t) => {
        if (t <= 1) {
          clearRoundTimer();
          finishRound();
          return 0;
        }
        return t - 1;
      });
    }, 1000);
  }, [clearRoundTimer, difficulty, finishRound]);

  const handleRoundInput = useCallback((e) => {
    if (phase !== 'typing') return;
    e.preventDefault();

    if (e.repeat) return;
    if (isModifierShortcut(e)) return;

    const now = performance.now();

    if (e.key === 'Backspace') {
      if (positionRef.current <= 0) return;

      backspacesRef.current += 1;
      correctedRef.current += 1;
      setLiveBackspaces(backspacesRef.current);
      positionRef.current -= 1;
      setPosition(positionRef.current);
      keyEventsRef.current.push({ key: 'Backspace', correct: false, isBackspace: true, down: now });
      if (lastKeyPerfRef.current != null) {
        intervalsRef.current.push(now - lastKeyPerfRef.current);
      }
      lastKeyPerfRef.current = now;
      return;
    }

    if (e.key.length !== 1) return;

    const expected = passageRefText.current[positionRef.current];
    if (expected == null) return;

    // Timer starts on the first printable attempt (correct or incorrect), never resets mid-round.
    startTimingIfNeeded(now);

    if (e.key === expected) {
      keyEventsRef.current.push({ key: e.key, correct: true, down: now });
      if (lastKeyPerfRef.current != null) {
        intervalsRef.current.push(now - lastKeyPerfRef.current);
      }
      lastKeyPerfRef.current = now;
      positionRef.current += 1;
      setPosition(positionRef.current);

      keyDownMapRef.current.set(e.key, now);

      if (positionRef.current >= passageRefText.current.length) {
        finishRound();
      }
      return;
    }

    incorrectRef.current += 1;
    keyEventsRef.current.push({ key: e.key, correct: false, down: now });
    if (lastKeyPerfRef.current != null) {
      intervalsRef.current.push(now - lastKeyPerfRef.current);
    }
    lastKeyPerfRef.current = now;
    setWrongFlash(true);
    if (wrongFlashRef.current) clearTimeout(wrongFlashRef.current);
    wrongFlashRef.current = setTimeout(() => setWrongFlash(false), WRONG_FLASH_MS);
  }, [finishRound, phase, startTimingIfNeeded]);

  const handleKeyUp = useCallback((e) => {
    const downAt = keyDownMapRef.current.get(e.key);
    if (downAt == null) return;
    keyDownMapRef.current.delete(e.key);
    const dwell = performance.now() - downAt;
    dwellsRef.current.push(dwell);
    const idx = keyEventsRef.current.findLastIndex((k) => k.key === e.key && k.correct && k.dwell == null);
    if (idx >= 0) {
      keyEventsRef.current[idx] = { ...keyEventsRef.current[idx], up: performance.now(), dwell };
    }
  }, []);

  const handlePaste = useCallback((e) => {
    e.preventDefault();
  }, []);

  const handleFinish = useCallback(async () => {
    if (completedRef.current || savingRef.current || !aggregate) return;
    savingRef.current = true;
    setSaving(true);
    setSaveError('');
    try {
      await onComplete(aggregate);
      completedRef.current = true;
    } catch (error) {
      savingRef.current = false;
      setSaveError(error?.message || 'Could not save typing results. Please try again.');
    } finally {
      setSaving(false);
    }
  }, [aggregate, onComplete]);

  const progressPct = useMemo(() => {
    if (!passage.length) return 0;
    return Math.round((position / passage.length) * 100);
  }, [passage.length, position]);

  if (locked) return <LockedScreen onBack={onBack} />;

  return (
    <Page title="Typing Biometrics" onBack={onBack}>
      {phase === 'intro' && (
        <Card style={{ maxWidth: 520, margin: '0 auto' }} className="fade-in">
          <div style={{ fontSize: 40, marginBottom: 12, textAlign: 'center' }}>⌨️</div>
          <h2 style={{ fontWeight: 600, textAlign: 'center', marginBottom: 10 }}>Typing Biometrics</h2>
          <p style={{ color: T.muted, fontSize: 14, lineHeight: 1.85, marginBottom: 14 }}>
            This assessment measures your typing rhythm, speed, accuracy, pauses, and corrections.
            You will complete three short guided rounds. Type at your normal pace — do not rush.
          </p>
          <ul style={{ color: T.muted, fontSize: 13, lineHeight: 1.8, marginBottom: 18, paddingLeft: 18 }}>
            <li>Follow the highlighted character in each passage.</li>
            <li>Timing begins on your first character attempt, not before.</li>
            <li>Use Backspace to fix mistakes when needed.</li>
          </ul>
          <Btn onClick={beginTest} primary style={{ width: '100%', padding: '13px' }}>
            Begin Typing Test
          </Btn>
        </Card>
      )}

      {phase === 'typing' && (
        <Card style={{ maxWidth: 640, margin: '0 auto' }} className="fade-in">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10, gap: 12, flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 600, fontSize: 14 }}>Round {roundIndex + 1} of {TOTAL_ROUNDS}</span>
            <span style={{ fontSize: 12, color: T.muted, textTransform: 'capitalize' }}>Level: {difficulty}</span>
            <span style={{ fontFamily: T.mono, fontSize: 18, fontWeight: 700, color: timerActive && timeLeft <= 10 ? T.red : T.teal }}>
              {timerActive ? `${timeLeft}s` : 'Ready'}
            </span>
          </div>

          <div style={{ height: 6, background: T.faint, borderRadius: 999, overflow: 'hidden', marginBottom: 16 }}>
            <div style={{ width: `${((roundIndex + progressPct / 100) / TOTAL_ROUNDS) * 100}%`, height: '100%', background: `linear-gradient(90deg,${T.tealDim},${T.blue})`, transition: 'width .25s ease' }} />
          </div>

          <p style={{ color: T.muted, fontSize: 12, marginBottom: 10 }}>
            Type the highlighted character. Correct characters turn green; mistakes flash red.
          </p>

          <div
            ref={passageRef}
            onMouseDown={(e) => e.preventDefault()}
            style={{
              background: T.surface,
              border: `1px solid ${T.faint}`,
              borderRadius: 10,
              padding: '16px 18px',
              fontSize: 17,
              lineHeight: 1.95,
              minHeight: 120,
              maxHeight: 220,
              overflowY: 'auto',
              marginBottom: 12,
              userSelect: 'none',
              cursor: 'default',
              fontFamily: T.mono,
            }}
          >
            {passage.split('').map((char, i) => {
              let color = T.muted;
              let background = 'transparent';
              let fontWeight = 400;
              if (i < position) {
                color = T.green;
              } else if (i === position) {
                color = wrongFlash ? T.red : '#041016';
                background = wrongFlash ? 'rgba(252,129,129,0.25)' : T.teal;
                fontWeight = 700;
              }
              return (
                <span
                  key={`${i}-${char}`}
                  ref={i === position ? currentCharRef : null}
                  style={{ color, background, fontWeight, borderRadius: 3, padding: char === ' ' ? '0 0.15em' : 0 }}
                >
                  {char === ' ' ? '\u00A0' : char}
                </span>
              );
            })}
          </div>

          <input
            ref={inputRef}
            type="text"
            value=""
            readOnly
            aria-label="Typing input"
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="off"
            spellCheck={false}
            onKeyDown={handleRoundInput}
            onKeyUp={handleKeyUp}
            onPaste={handlePaste}
            onDrop={handlePaste}
            onChange={() => {}}
            style={{
              width: '100%',
              border: `2px solid ${T.teal}`,
              borderRadius: 8,
              padding: '12px 14px',
              fontSize: 15,
              background: T.bg,
              color: T.text,
              outline: 'none',
            }}
            placeholder={timerActive ? 'Keep typing…' : 'Click here and type the first character…'}
          />

          <div style={{ display: 'flex', gap: 16, marginTop: 12, fontSize: 12, color: T.muted, flexWrap: 'wrap' }}>
            <span>Progress: {progressPct}%</span>
            <span>Characters: {position}/{passage.length}</span>
            <span>Backspaces: {liveBackspaces}</span>
          </div>
        </Card>
      )}

      {phase === 'intermission' && latestRound && (
        <Card style={{ maxWidth: 460, margin: '0 auto', textAlign: 'center' }} className="fade-in">
          <div style={{ fontSize: 34, marginBottom: 10 }}>📊</div>
          <h2 style={{ fontWeight: 600, marginBottom: 6 }}>Round {latestRound.round} Complete</h2>
          <p style={{ color: T.muted, fontSize: 13, marginBottom: 18 }}>
            Nice work. Review your round results, then continue when you are ready.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 22 }}>
            {[
              ['WPM', latestRound.wpm],
              ['Accuracy', `${latestRound.accuracy}%`],
              ['Errors', latestRound.errors],
            ].map(([label, value]) => (
              <div key={label} style={{ background: T.surface, border: `1px solid ${T.faint}`, borderRadius: 10, padding: '12px 8px' }}>
                <div style={{ fontSize: 11, color: T.muted, marginBottom: 4 }}>{label}</div>
                <div style={{ fontFamily: T.mono, fontSize: 20, fontWeight: 700, color: T.teal }}>{value}</div>
              </div>
            ))}
          </div>
          <Btn onClick={continueToNextRound} primary style={{ width: '100%', padding: '13px' }}>
            Continue to Next Round →
          </Btn>
        </Card>
      )}

      {phase === 'final' && aggregate && (
        <Card style={{ maxWidth: 520, margin: '0 auto', textAlign: 'center' }} className="fade-in">
          <div style={{ fontSize: 42, marginBottom: 10 }}>✅</div>
          <h2 style={{ fontWeight: 600, color: T.teal, marginBottom: 8 }}>Typing Assessment Complete</h2>
          <p style={{ color: T.muted, fontSize: 14, lineHeight: 1.7, marginBottom: 18 }}>
            Your keystroke biomarkers were captured across all three rounds and will be saved to today&apos;s session.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10, marginBottom: 12, textAlign: 'left' }}>
            {[
              ['Average WPM', aggregate.wpm],
              ['Average Accuracy', `${aggregate.accuracy}%`],
              ['Total Errors', aggregate.totalErrors],
              ['Backspaces', aggregate.backspaces],
              ['Rhythm Score', aggregate.rhythmScore],
              ['Duration', `${Math.round(aggregate.durationMs / 1000)}s`],
            ].map(([label, value]) => (
              <div key={label} style={{ background: T.surface, border: `1px solid ${T.faint}`, borderRadius: 10, padding: '12px 14px' }}>
                <div style={{ fontSize: 11, color: T.muted, marginBottom: 4 }}>{label}</div>
                <div style={{ fontFamily: T.mono, fontSize: 18, fontWeight: 700, color: T.text }}>{value}</div>
              </div>
            ))}
          </div>
          <p style={{ fontSize: 12, color: T.muted, marginBottom: 16, lineHeight: 1.6 }}>
            Consistency score reflects typing rhythm stability (lower timing variability yields a higher score).
          </p>
          {saveError && (
            <div style={{ background: 'rgba(252,129,129,0.12)', border: '1px solid rgba(252,129,129,0.35)', borderRadius: 8, padding: '9px 13px', color: T.red, fontSize: 13, marginBottom: 12 }}>
              {saveError}
            </div>
          )}
          <Btn
            onClick={handleFinish}
            primary
            disabled={saving || completedRef.current}
            style={{ width: '100%', padding: '13px' }}
          >
            {saving ? 'Saving…' : completedRef.current ? 'Saved' : 'Finish Assessment →'}
          </Btn>
        </Card>
      )}
    </Page>
  );
}
