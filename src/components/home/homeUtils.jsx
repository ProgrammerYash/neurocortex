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
    <div className="home-hero-brain-profile" aria-hidden="true">
      <svg viewBox="0 0 480 420" role="presentation" className="home-hero-brain-profile__svg">
        <defs>
          <linearGradient id="brainProfileGlow" x1="20%" y1="0%" x2="80%" y2="100%">
            <stop offset="0%" stopColor="#2dd4bf" stopOpacity="0.55" />
            <stop offset="55%" stopColor="#63b3ed" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#7c3aed" stopOpacity="0.12" />
          </linearGradient>
          <radialGradient id="brainCoreGlow" cx="45%" cy="42%" r="40%">
            <stop offset="0%" stopColor="#2dd4bf" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#2dd4bf" stopOpacity="0" />
          </radialGradient>
        </defs>
        <ellipse cx="230" cy="210" rx="170" ry="150" fill="url(#brainCoreGlow)" />
        <path
          className="home-hero-brain-profile__silhouette"
          d="M120 250 C95 205 98 145 135 105 C165 72 215 58 265 70 C315 82 350 115 365 155 C382 200 372 250 345 285 C315 325 260 350 205 345 C160 341 130 315 120 250 Z"
          fill="rgba(8,12,22,0.92)"
          stroke="rgba(45,212,191,0.55)"
          strokeWidth="2.2"
        />
        <path
          className="home-hero-brain-profile__lobe"
          d="M145 120 C175 95 220 88 255 98 C240 130 225 165 205 195 C175 170 155 145 145 120 Z"
          fill="none"
          stroke="rgba(99,179,237,0.35)"
          strokeWidth="1.2"
        />
        <path
          className="home-hero-brain-profile__lobe"
          d="M255 98 C295 108 330 135 345 175 C330 205 300 230 265 240 C275 205 278 165 270 130 Z"
          fill="none"
          stroke="rgba(45,212,191,0.32)"
          strokeWidth="1.2"
        />
        <path
          className="home-hero-brain-profile__sulci"
          d="M155 165 C190 150 230 145 270 155 M150 205 C195 190 240 188 285 200 M165 240 C210 225 255 222 300 235"
          fill="none"
          stroke="rgba(45,212,191,0.28)"
          strokeWidth="1.1"
        />
        <g className="home-hero-brain-profile__pathways">
          <path
            className="home-hero-brain-profile__signal"
            d="M170 150 C205 135 240 132 275 145"
            fill="none"
            stroke="rgba(45,212,191,0.55)"
            strokeWidth="1.6"
            strokeDasharray="6 10"
          />
          <path
            className="home-hero-brain-profile__signal"
            d="M160 205 C205 192 250 190 295 205"
            fill="none"
            stroke="rgba(99,179,237,0.5)"
            strokeWidth="1.4"
            strokeDasharray="5 9"
          />
          <path
            className="home-hero-brain-profile__signal"
            d="M185 250 C225 238 265 236 305 248"
            fill="none"
            stroke="rgba(167,139,250,0.45)"
            strokeWidth="1.3"
            strokeDasharray="4 8"
          />
        </g>
        {[
          [170, 150], [230, 138], [290, 152], [155, 205], [220, 198], [285, 208],
          [180, 250], [240, 242], [305, 252], [210, 118], [320, 165],
        ].map(([cx, cy], index) => (
          <g key={index} className="home-hero-brain-profile__node">
            <circle cx={cx} cy={cy} r="5.5" fill="#2dd4bf" />
            <circle cx={cx} cy={cy} r="10" fill="none" stroke="rgba(45,212,191,0.35)" strokeWidth="1" />
          </g>
        ))}
        <rect className="home-hero-brain-profile__scan" x="110" y="70" width="260" height="3" rx="1.5" fill="rgba(99,179,237,0.35)" />
        <g className="home-hero-brain-profile__grid" opacity="0.25">
          {[0, 1, 2, 3, 4].map(row => (
            <line key={`h-${row}`} x1="120" y1={90 + row * 55} x2="360" y2={90 + row * 55} stroke="rgba(99,179,237,0.18)" />
          ))}
        </g>
      </svg>
    </div>
  );
}

/** @deprecated replaced by profile brain visual in Phase 5C */
export function HeroVisual() {
  return <HeroBrainVisual />;
}
