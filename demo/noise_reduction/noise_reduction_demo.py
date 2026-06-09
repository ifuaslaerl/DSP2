import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

import dsp2._dsp2_core as core


def _append_output(storage, engine, node_id):
    storage.extend(engine.get_node_output(node_id, 0))


def _spectrum(samples, sample_rate):
    window = np.hanning(len(samples))
    magnitude = np.abs(np.fft.rfft(samples * window))
    frequencies = np.fft.rfftfreq(len(samples), d=1.0 / sample_rate)
    peak = float(np.max(magnitude)) if magnitude.size else 0.0
    if peak > 0.0:
        magnitude = magnitude / peak
    return frequencies, magnitude


def run_demo(output_path):
    sample_rate = 4096.0
    block_size = 256
    blocks = 24

    engine = core.Engine()
    engine.set_signal_parameters(sample_rate, block_size)

    clean = engine.add_node("SineOscillator")
    noise = engine.add_node("NoiseGenerator")
    mixer = engine.add_node("Add")
    filtered = engine.add_node("ButterworthFilter")

    engine.set_node_parameter(clean, "frequency", 80.0)
    engine.set_node_parameter(noise, "amplitude", 0.45)
    engine.set_node_parameter(noise, "seed", 12345.0)
    engine.set_node_parameter(filtered, "cutoff", 180.0)
    engine.set_node_parameter(filtered, "type", 0.0)

    engine.add_edge(clean, 0, mixer, 0)
    engine.add_edge(noise, 0, mixer, 1)
    engine.add_edge(mixer, 0, filtered, 0)

    core.get_logs()
    engine.prepare_engine()

    clean_samples = []
    noisy_samples = []
    filtered_samples = []

    for _ in range(blocks):
        engine.process_block()
        _append_output(clean_samples, engine, clean)
        _append_output(noisy_samples, engine, mixer)
        _append_output(filtered_samples, engine, filtered)

    logs = core.get_logs()

    clean_samples = np.asarray(clean_samples, dtype=float)
    noisy_samples = np.asarray(noisy_samples, dtype=float)
    filtered_samples = np.asarray(filtered_samples, dtype=float)
    time_axis = np.arange(len(clean_samples)) / sample_rate

    visible = min(len(clean_samples), 1400)
    spectrum_start = block_size * 2
    freq_noisy, mag_noisy = _spectrum(noisy_samples[spectrum_start:], sample_rate)
    freq_filtered, mag_filtered = _spectrum(filtered_samples[spectrum_start:], sample_rate)

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    fig, axs = plt.subplots(4, 1, figsize=(12, 9), constrained_layout=True)
    fig.suptitle("D(SP)^2 - Remocao de ruido com filtro Butterworth", fontsize=14)

    axs[0].plot(time_axis[:visible], clean_samples[:visible], color="#246a73", linewidth=1.4)
    axs[0].set_title("1. Sinal util gerado no grafo: senoide de 80 Hz")
    axs[0].set_ylabel("Amplitude")
    axs[0].grid(True, linestyle="--", alpha=0.4)

    axs[1].plot(time_axis[:visible], noisy_samples[:visible], color="#9c4f24", linewidth=1.0)
    axs[1].set_title("2. Sinal contaminado: senoide + ruido branco")
    axs[1].set_ylabel("Amplitude")
    axs[1].grid(True, linestyle="--", alpha=0.4)

    axs[2].plot(time_axis[:visible], filtered_samples[:visible], color="#376b2f", linewidth=1.4)
    axs[2].set_title("3. Saida filtrada: passa-baixa reduz componentes rapidas do ruido")
    axs[2].set_ylabel("Amplitude")
    axs[2].grid(True, linestyle="--", alpha=0.4)

    max_freq = 1000.0
    axs[3].plot(freq_noisy, mag_noisy, color="#9c4f24", linewidth=1.1, label="Antes do filtro")
    axs[3].plot(freq_filtered, mag_filtered, color="#376b2f", linewidth=1.1, label="Depois do filtro")
    axs[3].axvline(180.0, color="#333333", linestyle="--", linewidth=1.0, label="Corte 180 Hz")
    axs[3].set_xlim(0.0, max_freq)
    axs[3].set_title("4. Espectro: energia de alta frequencia e atenuada")
    axs[3].set_xlabel("Frequencia (Hz)")
    axs[3].set_ylabel("Magnitude normalizada")
    axs[3].legend(loc="upper right")
    axs[3].grid(True, linestyle="--", alpha=0.4)

    if logs:
        axs[3].text(
            0.99,
            0.02,
            f"logs C++: {len(logs)}",
            transform=axs[3].transAxes,
            ha="right",
            va="bottom",
            fontsize=9,
        )

    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"PNG gerado: {os.path.relpath(output_path, PROJECT_ROOT)}")


if __name__ == "__main__":
    default_output = os.path.join(PROJECT_ROOT, "demo", "noise_reduction", "noise_reduction.png")
    run_demo(sys.argv[1] if len(sys.argv) > 1 else default_output)
