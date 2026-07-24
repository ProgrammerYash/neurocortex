import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion.js';

export const BRAIN_ANIMATED_SRC = '/images/neurocortex-rotating-brain.webp';
export const BRAIN_STATIC_SRC = '/images/neurocortex-brain-static.webp';
export const BRAIN_WIDTH = 492;
export const BRAIN_HEIGHT = 282;

export function HeroBrainVisual() {
  const reduceMotion = usePrefersReducedMotion();
  const src = reduceMotion ? BRAIN_STATIC_SRC : BRAIN_ANIMATED_SRC;

  return (
    <div className="home-hero-brain-visual" aria-hidden="true">
      <div className="home-hero-brain-visual__glow" />
      <img
        className="home-hero-brain-visual__image"
        src={src}
        alt=""
        aria-hidden="true"
        loading="eager"
        decoding="async"
        width={BRAIN_WIDTH}
        height={BRAIN_HEIGHT}
        draggable={false}
      />
    </div>
  );
}
