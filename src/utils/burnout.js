// ── Burnout score helper (used in table + export) ────────────────────
// Weighted composite: stress×4 + fatigue×3 + (10-motivation)×3
// Returns null when survey data is unavailable.
export function calcBurnout(s) {
  try {
    const sv = s?.survey;
    if (!sv) return null;
    const stress     = Number(sv.stress)     || 0;
    const fatigue    = Number(sv.fatigue)    || 0;
    const motivation = Number(sv.motivation) || 5;
    return Math.min(100, Math.round(stress*4 + fatigue*3 + (10-motivation)*3));
  } catch { return null; }
}
