#!/usr/bin/env python3
"""
mlx-tts: TOML-driven TTS wrapper for mlx-audio on Apple Silicon

Installation:
    pip install mlx-audio soundfile
    # Python < 3.11 also needs: pip install tomli

Usage:
    python mlx_tts.py config.toml
    python mlx_tts.py config.toml --dry-run

Output paths are derived automatically from the TOML filename:
    - [script]    -> ./<stem>.<format>
    - [[script]]  -> ./<stem>/<stem>_000.<format>, <stem>_001.<format>, ...

TOML format:

    format = "wav"   # wav | flac | mp3 (default: wav)
    model = "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit"

    [params]
    # Passed directly to model.generate() — any key accepted by the model is valid.
    voice = "Ryan"
    lang_code = "auto"
    speed = 1.0
    temperature = 0.9

    # --- Single text ---
    [script]
    text = \"\"\"
    Hello, world.
    \"\"\"

    # --- OR multiple texts ---
    # Reserved key per entry: text
    # All other keys override [params] for that entry.

    [[script]]
    text = "First."
    voice = "Ryan"

    [[script]]
    text = "Second."
    voice = "Vivian"

Notes on specific models:
    - IndexTTS : ref_audio is a required argument with no default.
                 Must be specified in [params] or the [[script]] entry.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Any

_RESERVED_KEYS = {"text", "enabled"}


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def load_config(toml_path: str) -> dict:
    try:
        import tomllib          # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            print(
                "[error] tomllib not found.\n"
                "  Python 3.11+ has it built-in.\n"
                "  For older versions: pip install tomli",
                file=sys.stderr,
            )
            sys.exit(1)

    path = Path(toml_path)
    if not path.exists():
        print(f"[error] Config file not found: {toml_path}", file=sys.stderr)
        sys.exit(1)

    with open(path, "rb") as f:
        return tomllib.load(f)


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------

def _save_audio(audio_mx: Any, sample_rate: int, output_path: str, fmt: str) -> None:
    try:
        import numpy as np
        import soundfile as sf
    except ImportError:
        print("[error] soundfile not found. Run: pip install soundfile", file=sys.stderr)
        sys.exit(1)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(output_path, np.array(audio_mx), sample_rate, format=fmt.upper())


# ---------------------------------------------------------------------------
# Segment resolution
# ---------------------------------------------------------------------------

def _resolve_segments(cfg: dict, stem: str, fmt: str) -> list[dict]:
    """Return validated segment list, each with '_output' resolved.

    [script]   -> single dict  -> one output file
    [[script]] -> list of dict -> per-entry output files under <stem>/
    """
    script = cfg.get("script")

    if isinstance(script, list):
        # [[script]] — multiple entries
        out_dir = Path(stem)
        raw: list[dict] = [
            {**seg, "_output": str(out_dir / f"{stem}_{i:03d}.{fmt}"), "_enabled": seg.get("enabled", True)}
            for i, seg in enumerate(script)
        ]
    elif isinstance(script, dict):
        # [script] — single entry
        script_text = script.get("text", "").strip()
        if not script_text:
            print("[error] [script] text is empty.", file=sys.stderr)
            sys.exit(1)
        raw = [{**script, "text": script_text, "_output": f"{stem}.{fmt}", "_enabled": script.get("enabled", True)}]
    else:
        print(
            "[error] No text found. Add [script] text = '...' or [[script]] entries.",
            file=sys.stderr,
        )
        sys.exit(1)

    segments: list[dict] = []
    for i, seg in enumerate(raw):
        text = seg.get("text", "").strip()
        if not text and seg["_enabled"]:
            print(f"[warn] Segment {i} has empty text; skipping.", file=sys.stderr)
            continue
        segments.append({**seg, "text": text})

    if not any(s["_enabled"] for s in segments):
        print("[error] No enabled segments to process.", file=sys.stderr)
        sys.exit(1)

    return segments


def _build_params(global_params: dict, seg: dict) -> dict:
    """Merge global [params] with per-entry overrides (non-reserved keys)."""
    overrides = {k: v for k, v in seg.items() if k not in _RESERVED_KEYS and not k.startswith("_")}
    return {**global_params, **overrides}


# ---------------------------------------------------------------------------
# TTS generation
# ---------------------------------------------------------------------------

def _run_segment(text: str, model: Any, output_path: str,
                 params: dict, fmt: str) -> None:
    import mlx.core as mx

    preview = text[:80] + ("..." if len(text) > 80 else "")
    print(f"[tts] {preview}")
    t0 = time.time()

    result_or_iter = model.generate(text=text, **params)

    # Spark and similar models return a single GenerationResult, not an iterable.
    if hasattr(result_or_iter, "audio"):
        results = [result_or_iter]
    else:
        results = list(result_or_iter)

    if not results:
        print("[error] No audio was generated.", file=sys.stderr)
        return

    sample_rate = results[-1].sample_rate
    audio_chunks = [r.audio for r in results]
    audio = mx.concatenate(audio_chunks) if len(audio_chunks) > 1 else audio_chunks[0]

    _save_audio(audio, sample_rate, output_path, fmt)
    print(f"[tts] Done ({time.time() - t0:.1f}s) -> {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(
        description="mlx-tts: TOML-driven TTS for Apple Silicon",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("config", help="Path to TOML config file")
    p.add_argument("--dry-run", action="store_true",
                   help="Validate config and print plan without running TTS")
    args = p.parse_args()

    cfg = load_config(args.config)

    stem = Path(args.config).stem
    model_id: str = cfg.get("model", "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit")
    global_params: dict = cfg.get("params", {})
    out_fmt: str = cfg.get("format", "wav")
    segments = _resolve_segments(cfg, stem, out_fmt)

    enabled_count = sum(1 for s in segments if s["_enabled"])
    print(f"[config] Model    : {model_id}")
    print(f"[config] Segments : {len(segments)} ({enabled_count} enabled)")
    for i, seg in enumerate(segments):
        preview = seg["text"][:60] + ("..." if len(seg["text"]) > 60 else "")
        status = "" if seg["_enabled"] else " [disabled]"
        print(f"  [{i:03d}] {preview!r} -> {seg['_output']}{status}")

    if args.dry_run:
        print("\n[dry-run] Config OK. Exiting without generating audio.")
        return

    try:
        from mlx_audio.tts.utils import load_model
    except ImportError:
        print("[error] mlx-audio not found. Run: pip install mlx-audio", file=sys.stderr)
        sys.exit(1)

    print(f"\n[model] Loading {model_id} ...")
    t0 = time.time()
    model = load_model(model_id)
    print(f"[model] Loaded ({time.time() - t0:.1f}s)\n")

    for seg in segments:
        if not seg["_enabled"]:
            print(f"[skip] {seg['_output']} (disabled)")
            continue
        params = _build_params(global_params, seg)
        _run_segment(
            text=seg["text"],
            model=model,
            output_path=seg["_output"],
            params=params,
            fmt=out_fmt,
        )


if __name__ == "__main__":
    main()
