import { T } from '../../constants/tokens.js';

const SYNTHETIC_DEMO_BADGE_STYLE = {
  fontSize: 10,
  fontWeight: 600,
  letterSpacing: '0.04em',
  textTransform: 'uppercase',
  color: T.purple,
  background: 'rgba(167,139,250,0.15)',
  border: '1px solid rgba(167,139,250,0.35)',
  padding: '2px 8px',
  borderRadius: 999,
  whiteSpace: 'nowrap',
};

export default function SyntheticDemoBadge() {
  return <span style={SYNTHETIC_DEMO_BADGE_STYLE}>Synthetic Demo</span>;
}
