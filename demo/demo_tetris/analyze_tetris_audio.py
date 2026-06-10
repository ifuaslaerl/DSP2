import argparse
import os
import wave

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEMO_DIR = os.path.join(PROJECT_ROOT, "demo", "demo_tetris")
DEFAULT_WAV_PATH = os.path.join(DEMO_DIR, "tetris.wav")
DEFAULT_MIDI_PATH = os.path.join(DEMO_DIR, "tetris_6motors_v2_tuned.mid")
DEFAULT_OUTPUT_PREFIX = os.path.join(DEMO_DIR, "tetris_6motors_v2_tuned")
DEFAULT_START_TIME = 0.0
DEFAULT_DURATION = 10.0


def load_wav_mono(path):
    with wave.open(path, "rb") as wav:
        channel_count = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        frame_count = wav.getnframes()
        raw = wav.readframes(frame_count)

    if sample_width == 1:
        samples = np.frombuffer(raw, dtype=np.uint8).astype(np.float64)
        samples = (samples - 128.0) / 128.0
    elif sample_width == 2:
        samples = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    elif sample_width == 4:
        samples = np.frombuffer(raw, dtype="<i4").astype(np.float64) / 2147483648.0
    else:
        raise ValueError(f"sample width nao suportado: {sample_width} bytes")

    if channel_count > 1:
        samples = samples.reshape(-1, channel_count).mean(axis=1)

    return sample_rate, samples


def crop_samples(samples, sample_rate, start_time, duration):
    if start_time < 0.0:
        raise ValueError("--start-time deve ser maior ou igual a zero")
    if duration <= 0.0:
        raise ValueError("--duration deve ser maior que zero")

    start_sample = int(round(start_time * sample_rate))
    duration_samples = int(round(duration * sample_rate))
    end_sample = min(samples.size, start_sample + duration_samples)
    if start_sample >= samples.size:
        total_duration = samples.size / float(sample_rate)
        raise ValueError(
            f"--start-time {start_time:.3f}s excede a duracao do audio "
            f"({total_duration:.3f}s)"
        )

    return samples[start_sample:end_sample], start_sample / float(sample_rate)


def compute_stft(samples, sample_rate, fft_size, hop_size, time_offset=0.0):
    if samples.size < fft_size:
        padded = np.zeros(fft_size, dtype=np.float64)
        padded[: samples.size] = samples
        samples = padded

    frame_count = 1 + int(np.ceil((samples.size - fft_size) / float(hop_size)))
    padded_size = (frame_count - 1) * hop_size + fft_size
    padded = np.zeros(padded_size, dtype=np.float64)
    padded[: samples.size] = samples

    window = np.hanning(fft_size)
    spectrum = np.empty((fft_size // 2 + 1, frame_count), dtype=np.float64)

    for frame_index in range(frame_count):
        start = frame_index * hop_size
        frame = padded[start : start + fft_size] * window
        spectrum[:, frame_index] = np.abs(np.fft.rfft(frame))

    frequencies = np.fft.rfftfreq(fft_size, d=1.0 / sample_rate)
    times = time_offset + (
        np.arange(frame_count) * hop_size + fft_size * 0.5
    ) / sample_rate
    return frequencies, times, spectrum


def amplitude_to_db(magnitude):
    reference = float(np.max(magnitude)) if magnitude.size else 0.0
    if reference <= 0.0:
        return np.full_like(magnitude, -80.0)

    return 20.0 * np.log10(np.maximum(magnitude, reference * 1.0e-4) / reference)


def compute_chromagram(frequencies, magnitude):
    chroma = np.zeros((12, magnitude.shape[1]), dtype=np.float64)
    valid = frequencies > 20.0
    valid[0] = False

    midi_notes = np.rint(69.0 + 12.0 * np.log2(frequencies[valid] / 440.0)).astype(int)
    pitch_classes = np.mod(midi_notes, 12)
    weighted = magnitude[valid, :]

    for pitch_class in range(12):
        matching_bins = pitch_classes == pitch_class
        if np.any(matching_bins):
            chroma[pitch_class, :] = np.sum(weighted[matching_bins, :], axis=0)

    frame_max = np.max(chroma, axis=0, keepdims=True)
    np.divide(chroma, frame_max, out=chroma, where=frame_max > 0.0)
    return chroma


def plot_stft(output_path, frequencies, times, magnitude_db, max_frequency, time_label):
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    max_bin = int(np.searchsorted(frequencies, max_frequency, side="right"))

    fig, ax = plt.subplots(figsize=(13, 6), constrained_layout=True)
    image = ax.imshow(
        magnitude_db[:max_bin, :],
        origin="lower",
        aspect="auto",
        extent=[times[0], times[-1], frequencies[0], frequencies[max_bin - 1]],
        cmap="magma",
        vmin=-80.0,
        vmax=0.0,
    )
    ax.set_title(f"Tetris 3.1 - STFT do audio original ({time_label})")
    ax.set_xlabel("Tempo (s)")
    ax.set_ylabel("Frequencia (Hz)")
    fig.colorbar(image, ax=ax, label="Magnitude (dBFS relativo)")
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_chromagram(output_path, times, chroma, time_label):
    note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    fig, ax = plt.subplots(figsize=(13, 5), constrained_layout=True)
    image = ax.imshow(
        chroma,
        origin="lower",
        aspect="auto",
        extent=[times[0], times[-1], -0.5, 11.5],
        cmap="viridis",
        vmin=0.0,
        vmax=1.0,
    )
    ax.set_title(f"Tetris 3.1 - Cromograma do audio original ({time_label})")
    ax.set_xlabel("Tempo (s)")
    ax.set_ylabel("Classe de nota")
    ax.set_yticks(np.arange(12), note_names)
    fig.colorbar(image, ax=ax, label="Energia normalizada por frame")
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Gera STFT e cromograma para a variante 3.1 do demo Tetris."
    )
    parser.add_argument("--input", default=DEFAULT_WAV_PATH, help="WAV de entrada.")
    parser.add_argument(
        "--midi",
        default=DEFAULT_MIDI_PATH,
        help="MIDI 3.1 usado como referencia de nome/fluxo.",
    )
    parser.add_argument(
        "--output-prefix",
        default=DEFAULT_OUTPUT_PREFIX,
        help="Prefixo dos PNGs de saida.",
    )
    parser.add_argument("--fft-size", type=int, default=4096)
    parser.add_argument("--hop-size", type=int, default=512)
    parser.add_argument("--max-frequency", type=float, default=5000.0)
    parser.add_argument(
        "--start-time",
        type=float,
        default=DEFAULT_START_TIME,
        help="Inicio da janela analisada, em segundos.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=DEFAULT_DURATION,
        help="Duracao da janela analisada, em segundos.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if not os.path.exists(args.input):
        raise FileNotFoundError(args.input)
    if not os.path.exists(args.midi):
        raise FileNotFoundError(args.midi)

    sample_rate, samples = load_wav_mono(args.input)
    samples, actual_start_time = crop_samples(
        samples,
        sample_rate,
        args.start_time,
        args.duration,
    )
    actual_duration = samples.size / float(sample_rate)
    time_label = f"{actual_start_time:.2f}s-{actual_start_time + actual_duration:.2f}s"
    frequencies, times, magnitude = compute_stft(
        samples,
        sample_rate,
        args.fft_size,
        args.hop_size,
        time_offset=actual_start_time,
    )
    magnitude_db = amplitude_to_db(magnitude)
    chroma = compute_chromagram(frequencies, magnitude)

    stft_path = f"{args.output_prefix}_stft.png"
    chromagram_path = f"{args.output_prefix}_chromagram.png"
    plot_stft(stft_path, frequencies, times, magnitude_db, args.max_frequency, time_label)
    plot_chromagram(chromagram_path, times, chroma, time_label)

    print(f"WAV: {os.path.relpath(args.input, PROJECT_ROOT)}")
    print(f"MIDI 3.1: {os.path.relpath(args.midi, PROJECT_ROOT)}")
    print(f"STFT: {os.path.relpath(stft_path, PROJECT_ROOT)}")
    print(f"Cromograma: {os.path.relpath(chromagram_path, PROJECT_ROOT)}")
    print(
        "Parametros: "
        f"sample_rate={sample_rate}, fft_size={args.fft_size}, "
        f"hop_size={args.hop_size}, janela={time_label}"
    )


if __name__ == "__main__":
    main()
