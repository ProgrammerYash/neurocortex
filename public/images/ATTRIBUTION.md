# Rotating brain animation assets

## Source animation

- **Supplied URL:** https://media.beehiiv.com/cdn-cgi/image/fit=scale-down,quality=80,format=auto,onerror=redirect/uploads/asset/file/203f2dd6-7c4d-453a-a713-a7dda5e93418/giphy__3_.gif
- **Apparent original filename:** `giphy__3_.gif`
- **Local development source:** `scripts/assets/source-rotating-brain.gif`
- **Creator:** Unknown (not verified)
- **License:** Unknown — **must be reviewed before any final public competition submission**

NeuroCortex does **not** claim ownership of the original animation. The homepage uses processed derivatives only:

- `public/images/neurocortex-rotating-brain.webp` — animated WebP with transparent background and optimized frame count
- `public/images/neurocortex-brain-static.webp` — static reduced-motion frame with transparent background

## Processing

Build-time script: `scripts/process-brain-animation.py`

The source GIF uses a plain black background. The script measures near-black border pixels, flood-fills connected background from the frame edges, applies a soft distance-based alpha ramp, feathers edges, temporally stabilizes alpha, adds transparent padding, deduplicates similar frames, and exports optimized animated WebP.

Do **not** hotlink the Beehiiv CDN URL or the raw source GIF at runtime.
