export default function WorkInProgressPanel({ size = 'standard', label = 'Work in Progress' }) {
  return (
    <div
      className={`home-wip-panel home-wip-panel--${size} home-card--hover`}
      role="status"
      aria-label={label}
    >
      <div className="home-wip-panel__grid" aria-hidden="true" />
      <p className="home-wip-panel__label">{label}</p>
      <div className="home-wip-panel__line" aria-hidden="true" />
    </div>
  );
}
