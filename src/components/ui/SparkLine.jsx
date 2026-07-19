import { T } from '../../constants/tokens.js';

export default function SparkLine({data, color, max}) {
  // Guard: ensure data is a proper array of numbers/nulls
  const arr = Array.isArray(data) ? data : [];
  const vals = arr.filter(v => v !== null && v !== undefined && !isNaN(Number(v)));
  if (vals.length < 2) {
    return <p style={{color:T.muted,fontSize:12,padding:"8px 0"}}>Need at least 2 data points to show trend.</p>;
  }
  const mn  = Math.min(...vals);
  // CRASH-8: if max is null/0/falsy but we have valid numbers, compute it
  const mx  = (max !== null && max !== undefined && max > 0) ? max : Math.max(...vals);
  const range = (mx - mn) || 1;   // prevent /0
  const W=560, H=60, PAD=20;
  const den = Math.max(arr.length - 1, 1); // CRASH-7: prevent /0
  const pts = arr.map((v,i) => {
    if (v === null || v === undefined || isNaN(Number(v))) return null;
    const x = PAD + (i / den) * (W - PAD*2);
    const y = H - ((Number(v) - mn) / range) * (H-10) - 5;
    return {x, y};
  }).filter(Boolean);
  if (pts.length < 2) return <p style={{color:T.muted,fontSize:12,padding:"8px 0"}}>Insufficient valid points.</p>;
  const polyPts = pts.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{overflow:"visible"}}>
      <polyline points={polyPts} fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      {pts.map((p,i) => <circle key={i} cx={p.x.toFixed(1)} cy={p.y.toFixed(1)} r="3.5" fill={color} />)}
    </svg>
  );
}
