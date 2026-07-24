#!/usr/bin/env python3
"""Build transparent brain animation assets from the black-background source GIF."""

from __future__ import annotations

import json
import sys
import time
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
SOURCE_GIF = ROOT / "scripts" / "assets" / "source-rotating-brain.gif"
OUT_ANIMATED = ROOT / "public" / "images" / "neurocortex-rotating-brain.webp"
OUT_STATIC = ROOT / "public" / "images" / "neurocortex-brain-static.webp"
OUT_META = ROOT / "scripts" / "assets" / "brain-animation-meta.json"

TARGET_MAX_WIDTH = 480
TARGET_MAX_BYTES = 5_000_000
PREFERRED_MAX_BYTES = 4_000_000
MAX_OUTPUT_FRAMES = 110
DEDUPE_MSE = 18.0

# Measured near-black background (border median) with soft alpha ramp.
BG_RGB = np.array([0.0, 0.0, 0.0], dtype=np.float32)
DIST_OPAQUE = 22.0
DIST_TRANSPARENT = 10.0
ALPHA_BLUR_SIGMA = 0.75
FLOOD_TOLERANCE = 11.0
CLOSE_ITER = 2


def load_gif_frames(path: Path) -> tuple[list[Image.Image], list[int], dict]:
    gif = Image.open(path)
    if gif.format != "GIF":
        raise RuntimeError(f"Expected GIF, got {gif.format}")
    header = path.read_bytes()[:6]
    if not header.startswith((b"GIF87a", b"GIF89a")):
        raise RuntimeError("Download does not appear to be a valid GIF file.")

    frames: list[Image.Image] = []
    durations: list[int] = []
    for index in range(gif.n_frames):
        gif.seek(index)
        frame = gif.convert("RGBA")
        if TARGET_MAX_WIDTH and frame.width > TARGET_MAX_WIDTH:
            new_h = max(1, round(frame.height * (TARGET_MAX_WIDTH / frame.width)))
            frame = frame.resize((TARGET_MAX_WIDTH, new_h), Image.Resampling.LANCZOS)
        frames.append(frame)
        durations.append(max(20, int(gif.info.get("duration", 66) or 66)))

    meta = {
        "detected_format": gif.format,
        "source_dimensions": [gif.size[0], gif.size[1]],
        "loaded_dimensions": [frames[0].width, frames[0].height],
        "source_frames": gif.n_frames,
        "source_duration_ms": sum(durations),
        "source_bytes": path.stat().st_size,
    }
    return frames, durations, meta


def measure_background_rgb(frames: list[Image.Image]) -> np.ndarray:
    samples: list[np.ndarray] = []
    for frame in frames[:: max(1, len(frames) // 12)]:
        rgb = np.array(frame.convert("RGB"), dtype=np.float32)
        border = np.concatenate(
            [
                rgb[0].reshape(-1, 3),
                rgb[-1].reshape(-1, 3),
                rgb[:, 0],
                rgb[:, -1],
            ],
            axis=0,
        )
        samples.append(border)
    stacked = np.concatenate(samples, axis=0)
    return np.median(stacked, axis=0)


def flood_background_mask(rgb: np.ndarray, bg: np.ndarray) -> np.ndarray:
    h, w, _ = rgb.shape
    dist = np.linalg.norm(rgb - bg, axis=2)
    near_bg = dist <= FLOOD_TOLERANCE
    background = np.zeros((h, w), dtype=bool)
    queue: deque[tuple[int, int]] = deque()

    for x in range(w):
        if near_bg[0, x]:
            queue.append((0, x))
        if near_bg[h - 1, x]:
            queue.append((h - 1, x))
    for y in range(h):
        if near_bg[y, 0]:
            queue.append((y, 0))
        if near_bg[y, w - 1]:
            queue.append((y, w - 1))

    while queue:
        y, x = queue.popleft()
        if background[y, x] or not near_bg[y, x]:
            continue
        background[y, x] = True
        if y > 0:
            queue.append((y - 1, x))
        if y + 1 < h:
            queue.append((y + 1, x))
        if x > 0:
            queue.append((y, x - 1))
        if x + 1 < w:
            queue.append((y, x + 1))

    return background


def frame_alpha(rgb: np.ndarray, bg: np.ndarray) -> np.ndarray:
    dist = np.linalg.norm(rgb - bg, axis=2)
    background = flood_background_mask(rgb, bg)

    alpha = np.zeros(dist.shape, dtype=np.float32)
    ramp = np.clip((dist - DIST_TRANSPARENT) / (DIST_OPAQUE - DIST_TRANSPARENT), 0.0, 1.0)
    alpha = np.where(background, 0.0, np.maximum(ramp, 0.85))

    fg_seed = alpha > 0.35
    fg_seed = ndimage.binary_closing(fg_seed, iterations=CLOSE_ITER)
    alpha = np.where(fg_seed, np.maximum(alpha, 0.92), alpha)
    alpha = np.where(background, 0.0, alpha)
    alpha = ndimage.gaussian_filter(alpha, ALPHA_BLUR_SIGMA)
    alpha = np.where(alpha < 0.04, 0.0, alpha)
    return np.clip(alpha, 0.0, 1.0)


def pad_transparent(frame: Image.Image, pixels: int = 6) -> Image.Image:
    width, height = frame.size
    padded = Image.new("RGBA", (width + pixels * 2, height + pixels * 2), (0, 0, 0, 0))
    padded.paste(frame, (pixels, pixels), frame)
    return padded


def dedupe_frames(
    frames: list[Image.Image],
    durations: list[int],
) -> tuple[list[Image.Image], list[int]]:
    if not frames:
        return frames, durations
    kept_frames = [frames[0]]
    kept_durations = [durations[0]]
    prev = np.array(frames[0].convert("RGB"), dtype=np.float32)
    for frame, duration in zip(frames[1:], durations[1:]):
        current = np.array(frame.convert("RGB"), dtype=np.float32)
        mse = float(np.mean((current - prev) ** 2))
        if mse < DEDUPE_MSE:
            kept_durations[-1] += duration
            continue
        kept_frames.append(frame)
        kept_durations.append(duration)
        prev = current
    return kept_frames, kept_durations


def limit_frames(
    frames: list[Image.Image],
    durations: list[int],
    max_frames: int,
) -> tuple[list[Image.Image], list[int]]:
    if len(frames) <= max_frames:
        return frames, durations
    total = sum(durations)
    indices = np.linspace(0, len(frames) - 1, max_frames, dtype=int)
    picked_frames = [frames[i] for i in indices]
    picked_durations = [max(20, int(round(total / max_frames)))] * max_frames
    return picked_frames, picked_durations


def rgba_frame(frame: Image.Image, alpha: np.ndarray) -> Image.Image:
    rgb = np.array(frame.convert("RGB"), dtype=np.uint8)
    rgba = np.dstack([rgb, (alpha * 255.0).astype(np.uint8)])
    return Image.fromarray(rgba, mode="RGBA")


def composite_preview(rgba: np.ndarray, background: tuple[int, int, int]) -> Image.Image:
    rgb = rgba[..., :3].astype(np.float32)
    alpha = rgba[..., 3:4].astype(np.float32) / 255.0
    bg = np.array(background, dtype=np.float32)
    out = rgb * alpha + bg * (1.0 - alpha)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def choose_static_index(alpha_stack: np.ndarray) -> int:
    scores = alpha_stack.mean(axis=(1, 2))
    start = int(alpha_stack.shape[0] * 0.35)
    end = int(alpha_stack.shape[0] * 0.65)
    window = scores[start:end]
    return int(start + np.argmax(window))


def validate_output(alpha_stack: np.ndarray, rgb_stack: np.ndarray) -> dict:
    border_alpha = np.concatenate(
        [
            alpha_stack[:, 0, :].reshape(alpha_stack.shape[0], -1),
            alpha_stack[:, -1, :].reshape(alpha_stack.shape[0], -1),
            alpha_stack[:, :, 0],
            alpha_stack[:, :, -1],
        ],
        axis=1,
    )
    border_mean = float(border_alpha.mean())
    border_max = float(border_alpha.max())
    center = alpha_stack[:, alpha_stack.shape[1] // 2, alpha_stack.shape[2] // 2]
    center_mean = float(center.mean())

    if border_max > 0.08:
        raise RuntimeError(f"Border alpha too high (max {border_max:.3f}).")
    if center_mean < 0.7:
        raise RuntimeError(f"Brain center alpha too low ({center_mean:.3f}).")

    # Reject obvious black halos on bright test background.
    sample_index = alpha_stack.shape[0] // 2
    rgba = np.dstack(
        [
            rgb_stack[sample_index].astype(np.uint8),
            (alpha_stack[sample_index] * 255).astype(np.uint8),
        ]
    )
    padded = pad_transparent(Image.fromarray(rgba, mode="RGBA"))
    comp = composite_preview(np.array(padded), (255, 0, 0))
    comp_arr = np.array(comp, dtype=np.float32)
    border_rgb = np.concatenate([comp_arr[0], comp_arr[-1], comp_arr[:, 0], comp_arr[:, -1]], axis=0)
    if float(border_rgb[:, 0].mean()) < 248.0:
        raise RuntimeError("Bright-background composite still shows a dark border/halo.")

    return {
        "border_alpha_mean": border_mean,
        "border_alpha_max": border_max,
        "center_alpha_mean": center_mean,
    }


def encode_animated(frames: list[Image.Image], durations: list[int], quality: int) -> None:
    frames[0].save(
        OUT_ANIMATED,
        format="WEBP",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        lossless=False,
        quality=quality,
        method=4,
    )


def main() -> int:
    if not SOURCE_GIF.exists():
        print(f"Missing source GIF: {SOURCE_GIF}", file=sys.stderr)
        return 1

    t0 = time.time()
    raw_frames, raw_durations, source_meta = load_gif_frames(SOURCE_GIF)
    bg = measure_background_rgb(raw_frames)

    rgb_stack = np.stack([np.array(frame.convert("RGB"), dtype=np.float32) for frame in raw_frames])
    alpha_stack = np.stack([frame_alpha(rgb, bg) for rgb in rgb_stack], axis=0)
    alpha_stack = ndimage.uniform_filter1d(alpha_stack, size=3, axis=0, mode="nearest")
    validate_output(alpha_stack, rgb_stack)

    processed = [pad_transparent(rgba_frame(frame, alpha)) for frame, alpha in zip(raw_frames, alpha_stack)]
    processed, out_durations = dedupe_frames(processed, raw_durations)
    processed, out_durations = limit_frames(processed, out_durations, MAX_OUTPUT_FRAMES)

    static_index = choose_static_index(
        np.stack([np.array(frame.getchannel("A"), dtype=np.float32) / 255.0 for frame in processed])
    )

    OUT_ANIMATED.parent.mkdir(parents=True, exist_ok=True)
    chosen_quality = 78
    for quality in (78, 75, 72):
        encode_animated(processed, out_durations, quality)
        size = OUT_ANIMATED.stat().st_size
        chosen_quality = quality
        if size <= TARGET_MAX_BYTES:
            break

    animated_bytes = OUT_ANIMATED.stat().st_size
    if animated_bytes > TARGET_MAX_BYTES:
        print(
            f"Warning: animated WebP is {animated_bytes} bytes (> {TARGET_MAX_BYTES}).",
            file=sys.stderr,
        )

    static_frame = processed[static_index]
    static_frame.save(OUT_STATIC, format="WEBP", lossless=False, quality=82, method=4)

    static_rgba = np.array(static_frame)
    composite_preview(static_rgba, (6, 9, 16)).save(
        ROOT / "scripts" / "assets" / "preview-hero-bg.webp"
    )
    composite_preview(static_rgba, (255, 255, 255)).save(
        ROOT / "scripts" / "assets" / "preview-white-bg.webp"
    )
    composite_preview(static_rgba, (0, 255, 0)).save(
        ROOT / "scripts" / "assets" / "preview-green-bg.webp"
    )

    meta = {
        **source_meta,
        "measured_background_rgb": [float(x) for x in bg],
        "dist_transparent": DIST_TRANSPARENT,
        "dist_opaque": DIST_OPAQUE,
        "flood_tolerance": FLOOD_TOLERANCE,
        "alpha_blur_sigma": ALPHA_BLUR_SIGMA,
        "output_dimensions": [processed[0].width, processed[0].height],
        "output_frames": len(processed),
        "output_duration_ms": sum(out_durations),
        "animated_webp": str(OUT_ANIMATED.relative_to(ROOT)),
        "animated_bytes": animated_bytes,
        "webp_quality": chosen_quality,
        "static_webp": str(OUT_STATIC.relative_to(ROOT)),
        "static_bytes": OUT_STATIC.stat().st_size,
        "static_frame_index": static_index,
        "previous_animated_bytes": 11_615_662,
        "processing_seconds": round(time.time() - t0, 1),
    }
    OUT_META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
