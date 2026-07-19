import { useState, useRef, useCallback, useEffect } from 'react';
import { T } from '../../constants/tokens.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import LockedScreen from '../ui/LockedScreen.jsx';

const ROUNDS = 6;
const STIMULI = ['green', 'blue', 'yellow'];
const STIMULUS_COLORS = { green: '#68D391', blue: '#63B3ED', yellow: '#F6E05E' };

export default function ReactionTest({ onComplete, onBack, locked }) {
  const [phase, setPhase] = useState('intro');
  const [bkColor, setBkColor] = useState(T.bg);
  const [times, setTimes] = useState([]);
  const [missed, setMissed] = useState(0);
  const [feedbackMessage, setFeedbackMessage] = useState(null);

  const delayTimerRef = useRef(null);
  const responseTimerRef = useRef(null);
  const falseStartTimerRef = useRef(null);
  const nextRoundTimerRef = useRef(null);
  const finalizeTimerRef = useRef(null);
  const tapStartRef = useRef(null);
  const responseLockedRef = useRef(false);
  const timesRef = useRef([]);
  const missedRef = useRef(0);

  const clearAllTimers = useCallback(() => {
    if (delayTimerRef.current) {
      clearTimeout(delayTimerRef.current);
      delayTimerRef.current = null;
    }
    if (responseTimerRef.current) {
      clearTimeout(responseTimerRef.current);
      responseTimerRef.current = null;
    }
    if (falseStartTimerRef.current) {
      clearTimeout(falseStartTimerRef.current);
      falseStartTimerRef.current = null;
    }
    if (nextRoundTimerRef.current) {
      clearTimeout(nextRoundTimerRef.current);
      nextRoundTimerRef.current = null;
    }
    if (finalizeTimerRef.current) {
      clearTimeout(finalizeTimerRef.current);
      finalizeTimerRef.current = null;
    }
  }, []);

  useEffect(() => () => clearAllTimers(), [clearAllTimers]);

  const finalize = useCallback((validTimes, missedCount) => {
    const t = validTimes;
    if (!t.length) {
      onComplete({ avg: 0, median: 0, sd: 0, min: 0, max: 0, missed: missedCount, timestamp: Date.now() });
      return;
    }
    const avg = Math.round(t.reduce((a, b) => a + b, 0) / t.length);
    const s = [...t].sort((a, b) => a - b);
    const med = s[Math.floor(s.length / 2)];
    const sd = Math.round(Math.sqrt(t.reduce((sum, v) => sum + Math.pow(v - avg, 2), 0) / t.length));
    setPhase('results');
    finalizeTimerRef.current = setTimeout(
      () => onComplete({
        avg,
        median: med,
        sd,
        min: Math.min(...t),
        max: Math.max(...t),
        missed: missedCount,
        trials: ROUNDS,
        timestamp: Date.now(),
      }),
      1500,
    );
  }, [onComplete]);

  const afterValidMeasurement = useCallback((validTimes, missedCount) => {
    clearAllTimers();
    responseLockedRef.current = true;

    if (validTimes.length >= ROUNDS) {
      finalizeTimerRef.current = setTimeout(() => finalize(validTimes, missedCount), 400);
      return;
    }

    setPhase('waiting');
    nextRoundTimerRef.current = setTimeout(() => {
      startRoundRef.current();
    }, 800);
  }, [clearAllTimers, finalize]);

  const restartSameTrial = useCallback((message) => {
    clearAllTimers();
    responseLockedRef.current = true;
    setPhase('falseStart');
    setFeedbackMessage(message);
    setBkColor(T.surface);

    falseStartTimerRef.current = setTimeout(() => {
      falseStartTimerRef.current = null;
      startRoundRef.current();
    }, 1200);
  }, [clearAllTimers]);

  const startRoundRef = useRef(() => {});

  const startRound = useCallback(() => {
    clearAllTimers();
    responseLockedRef.current = false;
    setFeedbackMessage(null);
    setBkColor(T.surface);
    setPhase('waiting');
    tapStartRef.current = null;

    const delay = 1000 + Math.random() * 4000;
    delayTimerRef.current = setTimeout(() => {
      delayTimerRef.current = null;
      const stim = STIMULI[Math.floor(Math.random() * STIMULI.length)];
      setBkColor(STIMULUS_COLORS[stim]);
      setPhase('tap');
      tapStartRef.current = performance.now();

      responseTimerRef.current = setTimeout(() => {
        responseTimerRef.current = null;
        if (responseLockedRef.current) return;
        const nextMissed = missedRef.current + 1;
        missedRef.current = nextMissed;
        setMissed(nextMissed);
        restartSameTrial('Too slow! Get ready to try the same round again.');
      }, 2500);
    }, delay);
  }, [clearAllTimers, restartSameTrial]);

  startRoundRef.current = startRound;

  const handleFalseStart = useCallback(() => {
    if (responseLockedRef.current || phase !== 'waiting') return;
    restartSameTrial('Too soon! Wait for the color to change.');
  }, [phase, restartSameTrial]);

  const handleValidTap = useCallback(() => {
    if (phase !== 'tap' || responseLockedRef.current || tapStartRef.current == null) return;

    clearAllTimers();
    responseLockedRef.current = true;

    const rt = Math.round(performance.now() - tapStartRef.current);
    const nextTimes = [...timesRef.current, rt];
    timesRef.current = nextTimes;
    setTimes(nextTimes);
    afterValidMeasurement(nextTimes, missedRef.current);
  }, [phase, clearAllTimers, afterValidMeasurement]);

  const handleTap = () => {
    if (phase === 'falseStart') return;
    if (phase === 'waiting') {
      handleFalseStart();
      return;
    }
    if (phase === 'tap') {
      handleValidTap();
    }
  };

  const beginTest = () => {
    clearAllTimers();
    timesRef.current = [];
    missedRef.current = 0;
    setTimes([]);
    setMissed(0);
    setFeedbackMessage(null);
    responseLockedRef.current = false;
    startRound();
  };

  if (locked) return <LockedScreen onBack={onBack} />;

  const trialLabel = `Trial ${times.length + 1} of ${ROUNDS}`;

  return (
    <Page title="Reaction Time" onBack={onBack}>
      {phase === 'intro' && (
        <Card style={{ maxWidth: 400, margin: '0 auto', textAlign: 'center' }} className="fade-in">
          <div style={{ fontSize: 52, marginBottom: 16 }}>⚡</div>
          <h2 style={{ fontWeight: 600, marginBottom: 10 }}>Reaction Time Test</h2>
          <p style={{ color: T.muted, fontSize: 14, lineHeight: 1.8, marginBottom: 24 }}>
            {ROUNDS} rounds. When the screen changes color — tap immediately! Don't tap early or you'll need to repeat the round.
          </p>
          <Btn onClick={beginTest} primary style={{ padding: '13px 36px', fontSize: 15 }}>Begin Test</Btn>
        </Card>
      )}
      {(phase === 'waiting' || phase === 'tap' || phase === 'falseStart') && (
        <div
          onClick={handleTap}
          style={{
            position: 'fixed',
            inset: 0,
            background: bkColor,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: phase === 'falseStart' ? 'default' : 'pointer',
            userSelect: 'none',
            transition: 'background .1s',
          }}
        >
          {phase === 'falseStart' ? (
            <>
              <div style={{ color: T.red, fontSize: 28, fontWeight: 700, textAlign: 'center', padding: '0 24px' }}>
                {feedbackMessage}
              </div>
              <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: 16, marginTop: 16 }}>
                Restarting this trial…
              </div>
            </>
          ) : (
            <>
              <div style={{ color: phase === 'tap' ? '#000' : 'rgba(255,255,255,0.6)', fontSize: 56, fontWeight: 700 }}>
                {phase === 'waiting' ? '·  ·  ·' : 'TAP!'}
              </div>
              <div style={{ color: phase === 'tap' ? 'rgba(0,0,0,0.5)' : 'rgba(255,255,255,0.4)', fontSize: 16, marginTop: 16 }}>
                {phase === 'waiting' ? 'Wait for color change…' : 'Tap as fast as you can!'}
              </div>
            </>
          )}
          <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: 12, marginTop: 40 }}>
            {trialLabel}
          </div>
          {times.length > 0 && (
            <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: 13, marginTop: 8 }}>
              Last: {times[times.length - 1]}ms
            </div>
          )}
        </div>
      )}
      {phase === 'results' && (
        <Card style={{ maxWidth: 380, margin: '0 auto', textAlign: 'center' }} className="fade-in">
          <div style={{ fontSize: 40, marginBottom: 12 }}>✅</div>
          <h2 style={{ fontWeight: 600, color: T.teal }}>Complete!</h2>
          <p style={{ color: T.muted, fontSize: 14, marginTop: 8 }}>Saving biomarker data…</p>
          {times.length > 0 && (
            <div style={{ fontFamily: T.mono, fontSize: 20, color: T.teal, marginTop: 16 }}>
              {Math.round(times.reduce((a, b) => a + b, 0) / times.length)}ms avg
            </div>
          )}
        </Card>
      )}
    </Page>
  );
};
