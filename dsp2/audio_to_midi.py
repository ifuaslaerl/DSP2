import argparse
import json
import math
import os
import tempfile

import dsp2._dsp2_core as core
from dsp2.audio_io import load_wav_mono
from dsp2.graph_loader import GraphLoader
from dsp2.midi_io import write_midi_file


def build_audio_to_midi_graph(
    path,
    input_path,
    fft_size,
    peak_count,
    threshold,
    min_frequency,
    max_frequency,
    min_bin_distance,
):
    peak_parameters = {
        "peak_count": peak_count,
        "min_frequency": min_frequency,
        "threshold": threshold,
        "min_bin_distance": min_bin_distance,
    }
    if max_frequency is not None:
        peak_parameters["max_frequency"] = max_frequency

    graph = {
        "nodes": [
            {
                "name": "Audio",
                "type": "AudioFileInput",
                "parameters": {"path": input_path},
            },
            {
                "name": "Window",
                "type": "Windowing",
                "parameters": {"type": 0},
            },
            {
                "name": "Spectrum",
                "type": "SpectrumAnalyzer",
                "parameters": {"fft_size": fft_size},
            },
            {
                "name": "Peaks",
                "type": "SpectralPeakPicker",
                "parameters": peak_parameters,
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


def _validate_analysis_parameters(
    block_size,
    fft_size,
    peak_count,
    threshold,
    min_frequency,
    max_frequency,
    min_bin_distance,
):
    if block_size <= 0:
        raise ValueError("block_size deve ser positivo.")
    if fft_size <= 0:
        raise ValueError("fft_size deve ser positivo.")
    if peak_count <= 0:
        raise ValueError("peak_count deve ser positivo.")
    if threshold < 0.0:
        raise ValueError("threshold nao pode ser negativo.")
    if min_frequency < 0.0:
        raise ValueError("min_frequency nao pode ser negativo.")
    if max_frequency is not None and max_frequency <= min_frequency:
        raise ValueError("max_frequency deve ser maior que min_frequency.")
    if min_bin_distance < 0:
        raise ValueError("min_bin_distance nao pode ser negativo.")


def collect_midi_note_frames(
    input_path,
    block_size=2048,
    fft_size=None,
    peak_count=6,
    threshold=0.001,
    min_frequency=20.0,
    max_frequency=None,
    min_bin_distance=2,
):
    if fft_size is None:
        fft_size = block_size
    _validate_analysis_parameters(
        block_size,
        fft_size,
        peak_count,
        threshold,
        min_frequency,
        max_frequency,
        min_bin_distance,
    )

    samples, sample_rate = load_wav_mono(input_path)
    block_count = max(1, int(math.ceil(len(samples) / float(block_size))))

    with tempfile.TemporaryDirectory() as tmpdir:
        graph_path = os.path.join(tmpdir, "audio_to_midi_graph.json")
        build_audio_to_midi_graph(
            graph_path,
            os.path.abspath(input_path),
            fft_size,
            peak_count,
            threshold,
            min_frequency,
            max_frequency,
            min_bin_distance,
        )

        engine = core.Engine()
        engine.set_signal_parameters(float(sample_rate), block_size)
        node_ids = GraphLoader.load_from_json(engine, graph_path)
        core.get_logs()
        engine.prepare_engine()

        frames = []
        for _ in range(block_count):
            engine.process_block()
            notes = engine.get_node_output(node_ids["Midi"], 0)
            frames.append([int(round(note)) for note in notes if int(round(note)) > 0])

        logs = core.get_logs()

    return {
        "frames": frames,
        "sample_rate": sample_rate,
        "sample_count": len(samples),
        "block_count": block_count,
        "logs": logs,
    }


def export_audio_to_midi(
    input_path,
    output_path,
    block_size=2048,
    fft_size=None,
    peak_count=6,
    threshold=0.001,
    min_frequency=20.0,
    max_frequency=None,
    min_bin_distance=2,
    tempo_bpm=120.0,
    velocity=96,
    program=0,
    ppq=480,
):
    if tempo_bpm <= 0.0:
        raise ValueError("tempo_bpm deve ser positivo.")
    if ppq <= 0:
        raise ValueError("ppq deve ser positivo.")

    capture = collect_midi_note_frames(
        input_path,
        block_size=block_size,
        fft_size=fft_size,
        peak_count=peak_count,
        threshold=threshold,
        min_frequency=min_frequency,
        max_frequency=max_frequency,
        min_bin_distance=min_bin_distance,
    )

    ticks_per_second = ppq * (tempo_bpm / 60.0)
    frame_seconds = block_size / float(capture["sample_rate"])
    frame_ticks = max(1, int(round(frame_seconds * ticks_per_second)))

    midi_info = write_midi_file(
        output_path,
        capture["frames"],
        frame_ticks,
        tempo_bpm=tempo_bpm,
        velocity=velocity,
        program=program,
        ppq=ppq,
    )

    capture.update(midi_info)
    return capture


def main():
    parser = argparse.ArgumentParser(description="Exporta um WAV para MIDI usando o pipeline DSP2.")
    parser.add_argument("--input", required=True, help="Arquivo WAV PCM de entrada.")
    parser.add_argument("--output", required=True, help="Arquivo .mid de saida.")
    parser.add_argument("--block-size", type=int, default=2048, help="Tamanho de bloco de analise.")
    parser.add_argument("--fft-size", type=int, default=None, help="Tamanho da FFT; default igual ao block-size.")
    parser.add_argument("--peak-count", type=int, default=6, help="Numero maximo de notas simultaneas por bloco.")
    parser.add_argument("--threshold", type=float, default=0.001, help="Limiar minimo de potencia espectral.")
    parser.add_argument("--min-frequency", type=float, default=20.0, help="Menor frequencia analisada em Hz.")
    parser.add_argument("--max-frequency", type=float, default=None, help="Maior frequencia analisada em Hz.")
    parser.add_argument("--min-bin-distance", type=int, default=2, help="Distancia minima entre picos espectrais.")
    parser.add_argument("--tempo-bpm", type=float, default=120.0, help="Tempo do arquivo MIDI exportado.")
    parser.add_argument("--velocity", type=int, default=96, help="Velocidade MIDI das notas.")
    parser.add_argument("--program", type=int, default=0, help="Program change MIDI, default piano acustico.")
    parser.add_argument("--ppq", type=int, default=480, help="Pulsos MIDI por seminima.")

    args = parser.parse_args()
    result = export_audio_to_midi(
        args.input,
        args.output,
        block_size=args.block_size,
        fft_size=args.fft_size,
        peak_count=args.peak_count,
        threshold=args.threshold,
        min_frequency=args.min_frequency,
        max_frequency=args.max_frequency,
        min_bin_distance=args.min_bin_distance,
        tempo_bpm=args.tempo_bpm,
        velocity=args.velocity,
        program=args.program,
        ppq=args.ppq,
    )

    unique_notes = sorted({note for frame in result["frames"] for note in frame})
    print(f"MIDI gerado: {args.output}")
    print(f"Blocos processados: {result['block_count']}")
    print(f"Notas detectadas: {unique_notes}")
    if result["logs"]:
        print(f"Logs C++ coletados: {len(result['logs'])}")


if __name__ == "__main__":
    main()
