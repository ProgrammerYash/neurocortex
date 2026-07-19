// dateToday() returns "YYYY-MM-DD" for the current local date.
// Named explicitly to avoid shadowing component prop names.
export const dateToday = () => new Date().toISOString().split("T")[0];
export const today = dateToday; // backward-compat alias

// Returns "Xh MMm SSs" until midnight (next session unlock)
export function countdownToMidnight() {
  const now=new Date();
  const next=new Date(now.getFullYear(),now.getMonth(),now.getDate()+1,0,0,0);
  const ms=next-now;
  const h=Math.floor(ms/3600000);
  const m=Math.floor((ms%3600000)/60000);
  const s=Math.floor((ms%60000)/1000);
  return `${h}h ${String(m).padStart(2,"0")}m ${String(s).padStart(2,"0")}s`;
}
