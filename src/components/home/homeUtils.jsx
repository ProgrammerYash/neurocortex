import { useEffect, useRef } from 'react';

export function useReveal() {
  const ref = useRef(null);
  useEffect(() => {
    const node = ref.current;
    if (!node) return undefined;
    const reduced = typeof window.matchMedia === 'function'
      && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduced || typeof IntersectionObserver === 'undefined') {
      node.querySelectorAll('.home-reveal').forEach(el => el.classList.add('is-visible'));
      return undefined;
    }
    const observer = new IntersectionObserver(
      entries => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' },
    );
    node.querySelectorAll('.home-reveal').forEach(el => observer.observe(el));
    return () => observer.disconnect();
  }, []);
  return ref;
}

export function HeroBrainVisual() {
  return (
    <div className="home-hero-brain" aria-hidden="true">
      <svg viewBox="0 0 420 420" role="presentation" className="home-hero-brain__svg">
        <defs>
          <linearGradient id="brainGlow" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#2dd4bf" stopOpacity="0.45" />
            <stop offset="100%" stopColor="#63b3ed" stopOpacity="0.2" />
          </linearGradient>
          <filter id="brainSoftGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <ellipse cx="210" cy="210" rx="150" ry="130" fill="url(#brainGlow)" opacity="0.35" />
        <path
          className="home-hero-brain__outline"
          d="M210 70 C150 70 110 110 105 165 C95 165 85 185 88 210 C82 235 95 260 115 275 C115 310 150 340 210 345 C270 340 305 310 305 275 C325 260 338 235 332 210 C335 185 325 165 315 165 C310 110 270 70 210 70 Z"
          fill="rgba(12,18,30,0.85)"
          stroke="rgba(45,212,191,0.55)"
          strokeWidth="2"
          filter="url(#brainSoftGlow)"
        />
        <path
          d="M210 85 L210 330"
          stroke="rgba(99,179,237,0.35)"
          strokeWidth="1.5"
          strokeDasharray="4 6"
        />
        <g className="home-hero-brain__pathways">
          <path d="M130 160 Q170 140 210 150 T290 160" fill="none" stroke="rgba(45,212,191,0.4)" strokeWidth="1.2" />
          <path d="M125 210 Q170 195 210 205 T295 210" fill="none" stroke="rgba(99,179,237,0.35)" strokeWidth="1.2" />
          <path d="M140 260 Q175 280 210 270 T280 255" fill="none" stroke="rgba(45,212,191,0.35)" strokeWidth="1.2" />
        </g>
        {[
          [150, 150], [190, 130], [230, 135], [270, 155],
          [135, 205], [175, 195], [245, 200], [285, 215],
          [160, 265], [210, 285], [260, 270],
        ].map(([cx, cy], index) => (
          <g key={index} className="home-hero-brain__node">
            <circle cx={cx} cy={cy} r="5" fill="#2dd4bf" opacity="0.9" />
            <circle cx={cx} cy={cy} r="9" fill="none" stroke="rgba(45,212,191,0.35)" strokeWidth="1" />
          </g>
        ))}
        <rect className="home-hero-brain__scan" x="60" y="0" width="300" height="4" rx="2" fill="rgba(99,179,237,0.25)" />
      </svg>
    </div>
  );
}

/** @deprecated replaced by HeroBrainVisual in Phase 5B */
export function HeroVisual() {
  return <HeroBrainVisual />;
}
