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

export function HeroVisual() {
  return (
    <div className="home-hero-visual" aria-hidden="true">
      <svg viewBox="0 0 400 400" role="presentation">
        <defs>
          <radialGradient id="homeGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#2dd4bf" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#2dd4bf" stopOpacity="0" />
          </radialGradient>
        </defs>
        <circle cx="200" cy="200" r="160" fill="url(#homeGlow)" />
        <circle cx="200" cy="200" r="120" fill="none" stroke="rgba(99,179,237,0.25)" strokeWidth="1" />
        <circle cx="200" cy="200" r="80" fill="none" stroke="rgba(45,212,191,0.35)" strokeWidth="1" strokeDasharray="4 6" />
        {[
          [200, 80], [320, 140], [340, 260], [260, 340], [140, 320], [60, 220], [100, 120],
        ].map(([cx, cy], index) => (
          <g key={index} className="home-hero-visual__node">
            <circle cx={cx} cy={cy} r="8" fill="#2dd4bf" opacity="0.85" />
            <line x1="200" y1="200" x2={cx} y2={cy} stroke="rgba(99,179,237,0.35)" strokeWidth="1" />
          </g>
        ))}
        <path d="M120 200 Q200 120 280 200 T120 200" fill="none" stroke="rgba(167,139,250,0.45)" strokeWidth="1.5" />
      </svg>
    </div>
  );
}
