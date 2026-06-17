"""
Common audio provider wrapper.

Use this when callers need one interface for WaveSpeed, Supertonic, or future TTS engines.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from services.wavespeed.client import WaveSpeedClient
from .tenant_provider_config import tenant_provider_config_resolver
from . import supertonic_tts


@dataclass
class AudioProviderResult:
    audio_bytes: bytes
    provider: str
    model: str
    voice_id: str
    meta: Dict[str, Any]


class AudioProvider:
    """Base interface for TTS providers."""

    provider_name = "base"
    model_name = "base"

    def synthesize(
        self,
        *,
        text: str,
        voice_id: str,
        custom_voice_id: Optional[str] = None,
        speed: float = 1.0,
        volume: float = 1.0,
        pitch: float = 0.0,
        emotion: str = "happy",
        user_id: Optional[str] = None,
        **kwargs: Any,
    ) -> AudioProviderResult:
        raise NotImplementedError


class WaveSpeedAudioProvider(AudioProvider):
    provider_name = "wavespeed"
    model_name = "minimax/speech-02-hd"

    def _client(self, user_id: Optional[str]) -> WaveSpeedClient:
        key, _source = tenant_provider_config_resolver.resolve_provider_key("wavespeed", user_id=user_id)
        return WaveSpeedClient(api_key=key)

    def synthesize(self, *, text: str, voice_id: str, custom_voice_id: Optional[str] = None,
                   speed: float = 1.0, volume: float = 1.0, pitch: float = 0.0,
                   emotion: str = "happy", user_id: Optional[str] = None, **kwargs: Any) -> AudioProviderResult:
        enable_sync_mode = kwargs.pop("enable_sync_mode", True)
        filtered_kwargs = {k: v for k, v in kwargs.items() if v is not None}
        audio_bytes = self._client(user_id).generate_speech(
            text=text,
            voice_id=voice_id,
            custom_voice_id=custom_voice_id,
            speed=speed,
            volume=volume,
            pitch=pitch,
            emotion=emotion,
            enable_sync_mode=enable_sync_mode,
            **filtered_kwargs,
        )
        return AudioProviderResult(
            audio_bytes=audio_bytes,
            provider=self.provider_name,
            model=self.model_name,
            voice_id=custom_voice_id or voice_id,
            meta={"voice_id": voice_id, "custom_voice_id": custom_voice_id},
        )


class SupertonicAudioProvider(AudioProvider):
    provider_name = "supertonic"
    model_name = "supertonic-3"

    def synthesize(self, *, text: str, voice_id: str = "F1", custom_voice_id: Optional[str] = None,
                   speed: float = 1.05, volume: float = 1.0, pitch: float = 0.0,
                   emotion: str = "happy", user_id: Optional[str] = None, **kwargs: Any) -> AudioProviderResult:
        # Supertonic local TTS ignores volume/pitch/emotion/custom_voice_id for now.
        lang = kwargs.pop("lang", None) or kwargs.pop("language", None) or "en"
        total_steps = int(kwargs.pop("total_steps", 8) or 8)
        silence_duration = float(kwargs.pop("silence_duration", 0.3) or 0.3)
        audio_bytes, meta = supertonic_tts.synthesize_speech(
            text,
            voice_name=voice_id,
            lang=lang,
            speed=speed,
            total_steps=total_steps,
            silence_duration=silence_duration,
        )
        return AudioProviderResult(
            audio_bytes=audio_bytes,
            provider=self.provider_name,
            model=self.model_name,
            voice_id=meta.get("voice") or voice_id,
            meta=meta,
        )


class AudioProviderFactory:
    @staticmethod
    def get(provider: Optional[str] = None, model: Optional[str] = None) -> AudioProvider:
        key = (provider or model or "wavespeed").lower()
        if "supertonic" in key:
            return SupertonicAudioProvider()
        if "minimax" in key or "wavespeed" in key:
            return WaveSpeedAudioProvider()
        # Safe default keeps old behavior.
        return WaveSpeedAudioProvider()
