"""
Supertonic TTS Service - On-device text-to-speech via Supertonic ONNX models.

Uses GPU (CUDA) when available, falls back to CPU.
No API key required. Runs entirely on server.
"""

from __future__ import annotations

import io
import logging
import os
import sys
import threading
from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# CUDA library path setup — must happen BEFORE onnxruntime import.
# The nvidia pip packages install CUDA/cuDNN libs inside the venv, but
# onnxruntime-gpu's provider plugin (.so) needs them on LD_LIBRARY_PATH.
# ---------------------------------------------------------------------------
_VENV_SITE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "venv", "lib", "python3.12", "site-packages",
)
# Also resolve for actual venv location (symlinked path)
if not os.path.isdir(_VENV_SITE):
    _VENV_SITE = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ".venv", "lib", "python3.12", "site-packages",
    )
_CUDA_LIB_DIRS = []
for _subdir in ("nvidia/cublas/lib", "nvidia/cudnn/lib", "nvidia/cuda_runtime/lib"):
    _p = os.path.join(_VENV_SITE, _subdir)
    if os.path.isdir(_p):
        _CUDA_LIB_DIRS.append(_p)
if _CUDA_LIB_DIRS:
    existing = os.environ.get("LD_LIBRARY_PATH", "")
    os.environ["LD_LIBRARY_PATH"] = ":".join(_CUDA_LIB_DIRS) + (f":{existing}" if existing else "")
    # Rehash so child processes / dlopen picks it up
    if hasattr(os, "execv"):
        try:
            os.environ["LD_LIBRARY_PATH"] = os.environ["LD_LIBRARY_PATH"]
        except Exception:
            pass

import numpy as np
import soundfile as sf
from loguru import logger
from supertonic import AVAILABLE_LANGUAGES

# ---------------------------------------------------------------------------
# Singleton: load model once, reuse across requests
# ---------------------------------------------------------------------------

_lock = threading.Lock()
_tts_instance = None


def _get_tts():
    """Return a shared Supertonic TTS instance (lazy-init, thread-safe)."""
    global _tts_instance
    if _tts_instance is not None:
        return _tts_instance
    with _lock:
        if _tts_instance is not None:
            return _tts_instance

        # --- GPU detection & monkeypatch ---
        # Supertonic defaults to CPUExecutionProvider. Override to use CUDA when available.
        import onnxruntime as ort
        available = ort.get_available_providers()
        if "CUDAExecutionProvider" in available:
            gpu_providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            logger.info("[supertonic] ✅ CUDA available — patching ONNX providers: %s", gpu_providers)
        else:
            gpu_providers = ["CPUExecutionProvider"]
            logger.info("[supertonic] ℹ️ CUDA not available — using CPU only")

        # CRITICAL: supertonic.loader does `from .config import DEFAULT_ONNX_PROVIDERS`
        # which creates a separate reference. Must modify the list in-place, not reassign.
        import supertonic.config as _st_config
        import supertonic.loader as _st_loader
        _st_config.DEFAULT_ONNX_PROVIDERS.clear()
        _st_config.DEFAULT_ONNX_PROVIDERS.extend(gpu_providers)
        if hasattr(_st_loader, 'DEFAULT_ONNX_PROVIDERS'):
            _st_loader.DEFAULT_ONNX_PROVIDERS.clear()
            _st_loader.DEFAULT_ONNX_PROVIDERS.extend(gpu_providers)

        logger.info("[supertonic] Loading Supertonic TTS model (supertonic-3, 31 langs)...")
        from supertonic import TTS
        tts = TTS(model="supertonic-3")

        # Log actual providers used by each ONNX session
        for attr_name in ("dp_ort", "text_enc_ort", "vector_est_ort", "vocoder_ort"):
            sess = getattr(tts.model, attr_name, None)
            if sess and hasattr(sess, "get_providers"):
                logger.info("[supertonic]   %s → %s", attr_name, sess.get_providers())

        logger.info(
            "[supertonic] Model loaded. Sample rate=%d, voices=%s..., multilingual=%s",
            tts.sample_rate,
            tts.voice_style_names[:5],
            tts.is_multilingual,
        )
        _tts_instance = tts
        return _tts_instance


# ---------------------------------------------------------------------------
# Voice style name → Style object cache
# ---------------------------------------------------------------------------

_style_cache: dict = {}


def _resolve_voice(voice_name: Optional[str]):
    """
    Resolve a voice name to a Style object.

    Lookup order:
      1. Exact match in  (cache hit)
      2. TTS.get_voice_style(name)
      3. Fallback to first available style
    """
    tts = _get_tts()
    name = (voice_name or "").strip()

    if name in _style_cache:
        return _style_cache[name]

    if name:
        try:
            style = tts.get_voice_style(name)
            _style_cache[name] = style
            logger.debug(f"[supertonic] Resolved voice '{name}'")
            return style
        except Exception:
            logger.warning(f"[supertonic] Voice '{name}' not found, using fallback")

    # Fallback: first available voice
    fallback_name = tts.voice_style_names[0] if tts.voice_style_names else None
    if fallback_name:
        style = tts.get_voice_style(fallback_name)
        _style_cache[fallback_name] = style
        logger.info(f"[supertonic] Using fallback voice: {fallback_name}")
        return style

    raise RuntimeError("No voice styles available in Supertonic model")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def synthesize_speech(
    text: str,
    *,
    voice_name: Optional[str] = None,
    lang: str = "en",
    speed: float = 1.05,
    total_steps: int = 8,
    silence_duration: float = 0.3,
) -> Tuple[bytes, dict]:
    """
    Synthesize speech from text using Supertonic.

    Returns:
        (wav_bytes, meta) where wav_bytes is a complete WAV file as bytes,
        and meta is a dict with provider/model/voice/sample_rate info.
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")
    text = text.strip()

    tts = _get_tts()
    style = _resolve_voice(voice_name)

    # Validate lang
    if lang and lang not in AVAILABLE_LANGUAGES:
        logger.warning(f"[supertonic] Lang '{lang}' may not be supported, trying anyway")

    audio_np, durations = tts.synthesize(
        text,
        voice_style=style,
        total_steps=total_steps,
        speed=max(0.5, min(2.0, speed)),
        silence_duration=silence_duration,
        lang=lang if lang else "en",
    )

    # audio_np: tuple (audio_array, durations) or just array
    if isinstance(audio_np, tuple):
        audio_np = audio_np[0]

    # Normalize to float32 numpy array
    audio_np = np.asarray(audio_np, dtype=np.float32)

    # Supertonic returns shape (channels, samples) — transpose to (samples, channels)
    if audio_np.ndim == 2:
        audio_np = audio_np.T  # → (samples, channels)

    # Flatten to mono if stereo
    if audio_np.ndim > 1:
        audio_np = audio_np.mean(axis=1)

    # Clamp to [-1, 1]
    audio_np = np.clip(audio_np, -1.0, 1.0)

    sr = tts.sample_rate or 44100

    # Write WAV via soundfile into a BytesIO buffer
    buf = io.BytesIO()
    sf.write(buf, audio_np, sr, format="WAV", subtype="PCM_16")
    buf.seek(0)
    wav_bytes = buf.read()

    voice_label = getattr(style, 'name', voice_name) or voice_name or "default"
    meta = {
        "provider": "supertonic",
        "model": tts.model_name or "supertonic-3",
        "voice": voice_label,
        "sample_rate": sr,
        "duration_seconds": round(len(audio_np) / sr, 2),
        "lang": lang,
        "file_size": len(wav_bytes),
    }

    logger.info(
        f"[supertonic] ✅ Synthesized {len(text)} chars → "
        f"{meta['duration_seconds']}s, {len(wav_bytes)} bytes, voice={voice_label}"
    )
    return wav_bytes, meta


def get_available_voices() -> list[dict]:
    """Return list of available voice styles with names."""
    tts = _get_tts()
    voices = []
    for name in tts.voice_style_names:
        voices.append({"name": name, "provider": "supertonic"})
    return voices


def get_available_languages() -> list[str]:
    """Return list of supported language codes."""
    from supertonic import AVAILABLE_LANGUAGES
    return list(AVAILABLE_LANGUAGES)
