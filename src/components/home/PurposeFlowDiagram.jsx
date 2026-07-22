import { purpose } from '../../content/presentationContent.js';

const STAGE_ICONS = [
  (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="8" r="3.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M6 20c0-3.3 2.7-6 6-6s6 2.7 6 6" fill="none" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  ),
  (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 14c2-4 4-6 8-6s6 2 8 6" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M4 10c2-3 4-4 8-4s6 1 8 4" fill="none" stroke="currentColor" strokeWidth="1.5" opacity="0.6" />
    </svg>
  ),
  (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="6" cy="12" r="2" fill="currentColor" />
      <circle cx="12" cy="6" r="2" fill="currentColor" />
      <circle cx="18" cy="12" r="2" fill="currentColor" />
      <circle cx="12" cy="18" r="2" fill="currentColor" />
      <path d="M8 11l3-3M13 8l3 3M15 13l-3 3M9 15l-3-3" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  ),
  (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="4" y="5" width="16" height="14" rx="2" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M8 10h8M8 14h5" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  ),
];

export default function PurposeFlowDiagram() {
  const stages = purpose.flowStages;
  return (
    <div className="home-purpose-flow" aria-label="Project information flow">
      {stages.map((label, index) => (
        <div key={label} className="home-purpose-flow__segment">
          <div className="home-purpose-flow__node">
            <span className="home-purpose-flow__icon">{STAGE_ICONS[index]}</span>
            <span className="home-purpose-flow__text">{label}</span>
          </div>
          {index < stages.length - 1 ? (
            <div className="home-purpose-flow__connector" aria-hidden="true">
              <span className="home-purpose-flow__arrow" />
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}
