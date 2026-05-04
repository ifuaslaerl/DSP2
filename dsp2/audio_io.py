import wave

import numpy as np


def _decode_pcm_frames(raw_frames, sample_width):
    if sample_width == 1:
        values = np.frombuffer(raw_frames, dtype=np.uint8).astype(np.float64)
        return (values - 128.0) / 128.0

    if sample_width == 2:
        values = np.frombuffer(raw_frames, dtype="<i2").astype(np.float64)
        return values / 32768.0

    if sample_width == 3:
        bytes_in = np.frombuffer(raw_frames, dtype=np.uint8).reshape(-1, 3)
        values = (
            bytes_in[:, 0].astype(np.int32)
            | (bytes_in[:, 1].astype(np.int32) << 8)
            | (bytes_in[:, 2].astype(np.int32) << 16)
        )
        values = np.where(values & 0x800000, values | ~0xFFFFFF, values)
        return values.astype(np.float64) / 8388608.0

    if sample_width == 4:
        values = np.frombuffer(raw_frames, dtype="<i4").astype(np.float64)
        return values / 2147483648.0

    raise ValueError(f"WAV PCM com largura de amostra nao suportada: {sample_width} bytes.")


def load_wav_mono(path):
    """Carrega um WAV PCM e retorna amostras mono normalizadas e sample rate."""
    with wave.open(path, "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        frame_count = wav.getnframes()
        raw_frames = wav.readframes(frame_count)

    if channels <= 0:
        raise ValueError("WAV invalido: numero de canais deve ser positivo.")

    samples = _decode_pcm_frames(raw_frames, sample_width)
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)

    return samples.astype(float).tolist(), float(sample_rate)
