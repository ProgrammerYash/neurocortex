import { useEffect, useRef } from 'react';

export { HeroBrainVisual } from './HeroBrainVisual.jsx';

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
