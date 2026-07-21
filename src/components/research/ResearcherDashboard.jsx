import { useEffect, useState } from 'react';
import { T } from '../../constants/tokens.js';
import { fetchDashboardSummary } from '../../store/research.js';
import Btn from '../ui/Btn.jsx';
import Card from '../ui/Card.jsx';
import ParticipantsSection from './ParticipantsSection.jsx';
import { formatPercent, formatReaction, formatScale, formatSleep } from './ParticipantDetailsPanel.jsx';

function summaryValue(label, value, formatter = value => value) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return formatter(value);
}

export default function ResearcherDashboard({ onBack }) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = () => {
    setLoading(true);
    setError('');
    return fetchDashboardSummary()
      .then(data => setSummary(data))
      .catch(err => setError(err.message || 'Could not load dashboard summary.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  if (loading && !summary) {
    return (
      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '2rem 1rem 3rem' }}>
        <Card><p style={{ color: T.muted, textAlign: 'center', padding: 24 }}>Loading researcher dashboard…</p></Card>
      </div>
    );
  }

  if (error && !summary) {
    return (
      <div style={{ maxWidth: 900, margin: '0 auto', padding: '2rem 1rem 3rem' }}>
        <Card>
          <p role="alert" style={{ color: T.red, marginBottom: 12 }}>{error}</p>
          <Btn onClick={load}>Retry</Btn>
          <Btn onClick={onBack} style={{ marginLeft: 10 }}>← Sign Out</Btn>
        </Card>
      </div>
    );
  }

  const cards = [
    { label: 'Total Participants', value: summaryValue('Total Participants', summary?.totalParticipants), color: T.teal, icon: '👥' },
    { label: 'Total Sessions', value: summaryValue('Total Sessions', summary?.totalSessions), color: T.blue, icon: '📅' },
    { label: 'Active Participants in the Last 7 Days', value: summaryValue('Active', summary?.activeParticipants7d), color: T.green, icon: '✅' },
    { label: 'Average Session Completion', value: summaryValue('Completion', summary?.averageSessionCompletion, formatPercent), color: T.gold, icon: '🏆' },
    { label: 'Average Reaction Time', value: summaryValue('Reaction', summary?.averageReactionTimeMs, formatReaction), color: T.purple, icon: '⚡' },
    { label: 'Average Stress', value: summaryValue('Stress', summary?.averageStress, formatScale), color: T.red, icon: '😓' },
    { label: 'Average Fatigue', value: summaryValue('Fatigue', summary?.averageFatigue, formatScale), color: T.orange, icon: '😴' },
    { label: 'Average Sleep', value: summaryValue('Sleep', summary?.averageSleepHours, formatSleep), color: T.blue, icon: '🌙' },
    { label: 'Average Memory Accuracy', value: summaryValue('Memory', summary?.averageMemoryAccuracy, formatPercent), color: T.teal, icon: '🧩' },
  ];

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '1rem 1rem 3rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '1rem 0 1.5rem', flexWrap: 'wrap' }}>
        <Btn onClick={onBack} style={{ padding: '8px 14px', fontSize: 13 }}>← Sign Out</Btn>
        <h1 style={{ fontWeight: 700, fontSize: 20, margin: 0 }}>Research Dashboard</h1>
        <span style={{ fontSize: 11, background: 'rgba(167,139,250,0.15)', color: T.purple, padding: '3px 10px', borderRadius: 20, border: '1px solid rgba(167,139,250,0.3)' }}>RESEARCHER</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10, marginBottom: 18 }}>
        {cards.map(({ label, value, color, icon }) => (
          <div key={label} style={{ background: T.card, border: `1px solid ${T.cardBorder}`, borderRadius: 12, padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 22 }}>{icon}</span>
            <div>
              <div style={{ fontSize: 10, color: T.muted, marginBottom: 2 }}>{label}</div>
              <div style={{ fontSize: 20, fontWeight: 700, color }}>{value}</div>
            </div>
          </div>
        ))}
      </div>

      <ParticipantsSection onSummaryRefresh={load} />
    </div>
  );
}
