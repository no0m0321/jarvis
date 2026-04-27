from __future__ import annotations

from typing import Any

import numpy as np
import sounddevice as sd


def record_until_silence(
    samplerate: int = 16000,
    silence_duration: float = 1.5,
    silence_threshold: float = 0.012,
    max_duration: float = 60.0,
    pre_speech_timeout: float = 8.0,
) -> "np.ndarray":
    """마이크에서 음성을 받아 침묵 감지 시 자동 종료.

    Args:
        samplerate: 16kHz mono float32 (Whisper 호환).
        silence_duration: 발화 후 이만큼 침묵하면 종료.
        silence_threshold: RMS threshold (마이크 환경에 따라 조정).
        max_duration: 안전 상한.
        pre_speech_timeout: 시작 직후 이만큼 침묵하면 빈 음성으로 종료.

    Returns:
        float32 numpy array (mono, 16kHz).
    """
    chunk_ms = 100
    chunk_samples = samplerate * chunk_ms // 1000
    silence_chunks_to_stop = int(silence_duration * 1000 / chunk_ms)
    pre_speech_chunks = int(pre_speech_timeout * 1000 / chunk_ms)
    max_chunks = int(max_duration * 1000 / chunk_ms)

    chunks: "list[Any]" = []
    silence_count = 0
    pre_silence_count = 0
    speech_started = False

    with sd.InputStream(
        samplerate=samplerate,
        channels=1,
        dtype="float32",
        blocksize=chunk_samples,
    ) as stream:
        for _ in range(max_chunks):
            data, _overflowed = stream.read(chunk_samples)
            chunks.append(data)
            rms = float(np.sqrt(np.mean(data ** 2)))

            if rms > silence_threshold:
                speech_started = True
                silence_count = 0
            elif speech_started:
                silence_count += 1
                if silence_count >= silence_chunks_to_stop:
                    break
            else:
                pre_silence_count += 1
                if pre_silence_count >= pre_speech_chunks:
                    return np.zeros(0, dtype=np.float32)

    return np.concatenate(chunks).flatten().astype(np.float32)


def capture_phrase(
    samplerate: int = 16000,
    silence_duration: float = 0.5,
    silence_threshold: float = 0.012,
    max_speech_duration: float = 10.0,
    max_wait_for_speech: float = 300.0,
    on_chunk_rms: "Any" = None,
) -> "np.ndarray":
    """발화가 시작될 때까지 대기 → 발화 캡처 → 침묵 시 종료.

    record_until_silence와 다른 점: 발화 시작 전에는 무한 대기(최대 max_wait_for_speech),
    발화 종료 침묵은 더 짧게(0.5초 기본). wake word 감지에 적합.
    """
    chunk_ms = 100
    chunk_samples = samplerate * chunk_ms // 1000
    silence_chunks_to_stop = int(silence_duration * 1000 / chunk_ms)
    max_speech_chunks = int(max_speech_duration * 1000 / chunk_ms)
    max_wait_chunks = int(max_wait_for_speech * 1000 / chunk_ms)

    chunks: "list[Any]" = []
    silence_count = 0
    speech_started = False
    wait_count = 0

    with sd.InputStream(
        samplerate=samplerate,
        channels=1,
        dtype="float32",
        blocksize=chunk_samples,
    ) as stream:
        while True:
            data, _overflowed = stream.read(chunk_samples)
            rms = float(np.sqrt(np.mean(data ** 2)))
            if on_chunk_rms is not None:
                try:
                    on_chunk_rms(rms)
                except Exception:
                    pass

            if rms > silence_threshold:
                speech_started = True
                chunks.append(data)
                silence_count = 0
                if len(chunks) >= max_speech_chunks:
                    break
            elif speech_started:
                chunks.append(data)
                silence_count += 1
                if silence_count >= silence_chunks_to_stop:
                    break
            else:
                wait_count += 1
                if wait_count >= max_wait_chunks:
                    return np.zeros(0, dtype=np.float32)

    if not chunks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(chunks).flatten().astype(np.float32)
