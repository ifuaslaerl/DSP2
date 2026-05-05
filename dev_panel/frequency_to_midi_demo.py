import json
import os
import struct
import sys
import tempfile
import wave

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import dsp2._dsp2_core as core
from dsp2.graph_loader import GraphLoader


def midi_note_name(note):
    if note <= 0:
        return "pad"
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    rounded = int(round(note))
    octave = (rounded // 12) - 1
    return f"{names[rounded % 12]}{octave}"


def write_demo_wav(path, samples, sample_rate):
    pcm = np.round(np.clip(samples, -1.0, 1.0) * 30000.0).astype("<i2")
    with wave.open(path, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(struct.pack("<" + "h" * len(pcm), *pcm.tolist()))


def build_graph_json(path, wav_path, block_size):
    graph = {
        "nodes": [
            {
                "name": "Audio",
                "type": "AudioFileInput",
                "parameters": {"path": wav_path},
            },
            {
                "name": "Window",
                "type": "Windowing",
                "parameters": {"type": 0},
            },
            {
                "name": "Spectrum",
                "type": "SpectrumAnalyzer",
                "parameters": {"fft_size": block_size},
            },
            {
                "name": "Peaks",
                "type": "SpectralPeakPicker",
                "parameters": {
                    "peak_count": 2,
                    "min_frequency": 20.0,
                    "threshold": 0.001,
                    "min_bin_distance": 2,
                },
            },
            {
                "name": "Midi",
                "type": "FrequencyToMidiNote",
            },
        ],
        "edges": [
            {"source": "Audio", "source_port": 0, "dest": "Window", "dest_port": 0},
            {"source": "Window", "source_port": 0, "dest": "Spectrum", "dest_port": 0},
            {"source": "Spectrum", "source_port": 0, "dest": "Peaks", "dest_port": 0},
            {"source": "Spectrum", "source_port": 1, "dest": "Peaks", "dest_port": 1},
            {"source": "Peaks", "source_port": 0, "dest": "Midi", "dest_port": 0},
        ],
    }
    with open(path, "w", encoding="utf-8") as graph_file:
        json.dump(graph, graph_file, indent=2)


def run_demo(output_path):
    sample_rate = 1024
    block_size = 256
    frequencies = [80.0, 200.0]
    amplitudes = [1.0, 0.7]
    time = np.arange(block_size) / sample_rate
    samples = (
        amplitudes[0] * np.sin(2.0 * np.pi * frequencies[0] * time)
        + amplitudes[1] * np.sin(2.0 * np.pi * frequencies[1] * time)
    ) / sum(amplitudes)

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        wav_path = os.path.join(tmpdir, "frequency_to_midi_input.wav")
        graph_path = os.path.join(tmpdir, "frequency_to_midi_graph.json")
        write_demo_wav(wav_path, samples, sample_rate)
        build_graph_json(graph_path, wav_path, block_size)

        engine = core.Engine()
        engine.set_signal_parameters(float(sample_rate), block_size)
        node_ids = GraphLoader.load_from_json(engine, graph_path)
        core.get_logs()
        engine.prepare_engine()
        engine.process_block()

        peak_frequencies = np.asarray(engine.get_node_output(node_ids["Peaks"], 0), dtype=float)
        peak_powers = np.asarray(engine.get_node_output(node_ids["Peaks"], 1), dtype=float)
        midi_notes = np.asarray(engine.get_node_output(node_ids["Midi"], 0), dtype=float)
        logs = core.get_logs()

    order = np.argsort(peak_frequencies)
    peak_frequencies = peak_frequencies[order]
    peak_powers = peak_powers[order]
    midi_notes = midi_notes[order]
    labels = [f"{int(round(note))} ({midi_note_name(note)})" for note in midi_notes]

    fig, axs = plt.subplots(3, 1, figsize=(11, 8), constrained_layout=True)
    fig.suptitle("D(SP)^2 - FrequencyToMidiNote Demo", fontsize=14)

    axs[0].plot(time, samples, color="#2f6f8f", linewidth=1.5)
    axs[0].set_title("Input WAV sintetico: 80 Hz + 200 Hz")
    axs[0].set_xlabel("Tempo (s)")
    axs[0].set_ylabel("Amplitude")
    axs[0].grid(True, linestyle="--", alpha=0.45)

    bars = axs[1].bar(range(len(peak_frequencies)), peak_frequencies, color="#5c8f3d")
    axs[1].set_title("SpectralPeakPicker: frequencias detectadas")
    axs[1].set_ylabel("Hz")
    axs[1].set_xticks(range(len(peak_frequencies)), [f"pico {i + 1}" for i in range(len(peak_frequencies))])
    axs[1].grid(True, axis="y", linestyle="--", alpha=0.45)
    for bar, freq, power in zip(bars, peak_frequencies, peak_powers):
        axs[1].text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height(),
            f"{freq:.0f} Hz\npot {power:.3f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    bars = axs[2].bar(range(len(midi_notes)), midi_notes, color="#8f4f3d")
    axs[2].set_title("FrequencyToMidiNote: notas MIDI geradas")
    axs[2].set_ylabel("MIDI note")
    axs[2].set_ylim(0, max(70.0, float(np.max(midi_notes)) + 8.0))
    axs[2].set_xticks(range(len(midi_notes)), labels)
    axs[2].grid(True, axis="y", linestyle="--", alpha=0.45)
    for bar, note in zip(bars, midi_notes):
        axs[2].text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height(),
            f"{int(round(note))}",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    if logs:
        axs[2].text(
            0.99,
            0.02,
            f"logs C++: {len(logs)}",
            transform=axs[2].transAxes,
            ha="right",
            va="bottom",
            fontsize=9,
        )

    fig.savefig(output_path, dpi=150)
    plt.close(fig)

    print(f"PNG gerado: {output_path}")
    for frequency, note in zip(peak_frequencies, midi_notes):
        print(f"{frequency:.0f} Hz -> MIDI {int(round(note))} ({midi_note_name(note)})")


if __name__ == "__main__":
    default_output = os.path.join("dev_panel", "frequency_to_midi_demo.png")
    output = sys.argv[1] if len(sys.argv) > 1 else default_output
    run_demo(output)
