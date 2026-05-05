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
    mode="peaks",
    min_midi_note=36,
    max_midi_note=84,
    harmonic_count=6,
    relative_threshold=0.05,
    min_confidence=0.2,
):
    if mode not in {"peaks", "melody"}:
        raise ValueError("mode deve ser 'peaks' ou 'melody'.")

    nodes = [
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
    ]
    edges = [
        {"source": "Audio", "source_port": 0, "dest": "Window", "dest_port": 0},
        {"source": "Window", "source_port": 0, "dest": "Spectrum", "dest_port": 0},
    ]

    if mode == "peaks":
        peak_parameters = {
            "peak_count": peak_count,
            "min_frequency": min_frequency,
            "threshold": threshold,
            "min_bin_distance": min_bin_distance,
        }
        if max_frequency is not None:
            peak_parameters["max_frequency"] = max_frequency

        nodes.extend(
            [
                {
                    "name": "Peaks",
                    "type": "SpectralPeakPicker",
                    "parameters": peak_parameters,
                },
                {
                    "name": "Midi",
                    "type": "FrequencyToMidiNote",
                },
            ]
        )
        edges.extend(
            [
                {"source": "Spectrum", "source_port": 0, "dest": "Peaks", "dest_port": 0},
                {"source": "Spectrum", "source_port": 1, "dest": "Peaks", "dest_port": 1},
                {"source": "Peaks", "source_port": 0, "dest": "Midi", "dest_port": 0},
            ]
        )
    else:
        nodes.extend(
            [
                {
                    "name": "Pitch",
                    "type": "HarmonicPitchDetector",
                    "parameters": {
                        "min_midi_note": min_midi_note,
                        "max_midi_note": max_midi_note,
                        "harmonic_count": harmonic_count,
                        "relative_threshold": relative_threshold,
                        "min_confidence": min_confidence,
                    },
                },
                {
                    "name": "Midi",
                    "type": "FrequencyToMidiNote",
                },
            ]
        )
        edges.extend(
            [
                {"source": "Spectrum", "source_port": 0, "dest": "Pitch", "dest_port": 0},
                {"source": "Spectrum", "source_port": 1, "dest": "Pitch", "dest_port": 1},
                {"source": "Pitch", "source_port": 0, "dest": "Midi", "dest_port": 0},
            ]
        )

    graph = {"nodes": nodes, "edges": edges}
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
    mode,
    min_midi_note,
    max_midi_note,
    harmonic_count,
    relative_threshold,
    min_confidence,
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
    if mode not in {"peaks", "melody"}:
        raise ValueError("mode deve ser 'peaks' ou 'melody'.")
    if min_midi_note < 0 or max_midi_note > 127 or max_midi_note < min_midi_note:
        raise ValueError("faixa MIDI deve estar entre 0..127 e ser crescente.")
    if harmonic_count <= 0:
        raise ValueError("harmonic_count deve ser positivo.")
    if relative_threshold < 0.0:
        raise ValueError("relative_threshold nao pode ser negativo.")
    if min_confidence < 0.0:
        raise ValueError("min_confidence nao pode ser negativo.")


def _clamp_note(note, min_midi_note, max_midi_note):
    if note < min_midi_note:
        return min_midi_note
    if note > max_midi_note:
        return max_midi_note
    return note


def postprocess_note_frames(
    frames,
    min_midi_note=36,
    max_midi_note=84,
    min_note_frames=2,
    merge_gap_frames=1,
):
    if min_note_frames <= 0:
        raise ValueError("min_note_frames deve ser positivo.")
    if merge_gap_frames < 0:
        raise ValueError("merge_gap_frames nao pode ser negativo.")

    melody = []
    for frame in frames:
        if frame:
            melody.append(_clamp_note(int(round(frame[0])), min_midi_note, max_midi_note))
        else:
            melody.append(0)

    index = 0
    while index < len(melody):
        note = melody[index]
        if note == 0:
            index += 1
            continue

        end = index + 1
        while end < len(melody) and melody[end] == note:
            end += 1

        gap_end = end
        while gap_end < len(melody) and gap_end - end <= merge_gap_frames and melody[gap_end] == 0:
            gap_end += 1

        if gap_end < len(melody) and gap_end > end and melody[gap_end] == note:
            for fill in range(end, gap_end):
                melody[fill] = note
            continue

        index = end

    index = 0
    while index < len(melody):
        note = melody[index]
        if note == 0:
            index += 1
            continue

        end = index + 1
        while end < len(melody) and melody[end] == note:
            end += 1

        if end - index < min_note_frames:
            for clear in range(index, end):
                melody[clear] = 0

        index = end

    return [[note] if note > 0 else [] for note in melody]


def collect_midi_note_frames(
    input_path,
    block_size=2048,
    fft_size=None,
    peak_count=6,
    threshold=0.001,
    min_frequency=20.0,
    max_frequency=None,
    min_bin_distance=2,
    mode="peaks",
    min_midi_note=36,
    max_midi_note=84,
    harmonic_count=6,
    relative_threshold=0.05,
    min_confidence=0.2,
    min_note_frames=2,
    merge_gap_frames=1,
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
        mode,
        min_midi_note,
        max_midi_note,
        harmonic_count,
        relative_threshold,
        min_confidence,
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
            mode=mode,
            min_midi_note=min_midi_note,
            max_midi_note=max_midi_note,
            harmonic_count=harmonic_count,
            relative_threshold=relative_threshold,
            min_confidence=min_confidence,
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

    if mode == "melody":
        frames = postprocess_note_frames(
            frames,
            min_midi_note=min_midi_note,
            max_midi_note=max_midi_note,
            min_note_frames=min_note_frames,
            merge_gap_frames=merge_gap_frames,
        )

    return {
        "frames": frames,
        "sample_rate": sample_rate,
        "sample_count": len(samples),
        "block_count": block_count,
        "logs": logs,
        "mode": mode,
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
    mode="peaks",
    motor_mode="single",
    min_midi_note=36,
    max_midi_note=84,
    harmonic_count=6,
    relative_threshold=0.05,
    min_confidence=0.2,
    min_note_frames=2,
    merge_gap_frames=1,
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
        mode=mode,
        min_midi_note=min_midi_note,
        max_midi_note=max_midi_note,
        harmonic_count=harmonic_count,
        relative_threshold=relative_threshold,
        min_confidence=min_confidence,
        min_note_frames=min_note_frames,
        merge_gap_frames=merge_gap_frames,
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
        motor_mode=motor_mode,
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
    parser.add_argument("--mode", choices=["peaks", "melody"], default="peaks", help="Modo de transcricao.")
    parser.add_argument(
        "--motor-mode",
        choices=["single", "unison", "round-robin"],
        default="single",
        help="Distribuicao das notas nos motores MIDI 1..6.",
    )
    parser.add_argument("--min-midi-note", type=int, default=36, help="Menor nota MIDI no modo melody.")
    parser.add_argument("--max-midi-note", type=int, default=84, help="Maior nota MIDI no modo melody.")
    parser.add_argument("--harmonic-count", type=int, default=6, help="Numero de harmonicos no modo melody.")
    parser.add_argument("--relative-threshold", type=float, default=0.05, help="Limiar relativo no modo melody.")
    parser.add_argument("--min-confidence", type=float, default=0.2, help="Confianca minima no modo melody.")
    parser.add_argument("--min-note-frames", type=int, default=2, help="Duracao minima em blocos no modo melody.")
    parser.add_argument("--merge-gap-frames", type=int, default=1, help="Lacuna maxima para unir notas iguais.")
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
        mode=args.mode,
        motor_mode=args.motor_mode,
        min_midi_note=args.min_midi_note,
        max_midi_note=args.max_midi_note,
        harmonic_count=args.harmonic_count,
        relative_threshold=args.relative_threshold,
        min_confidence=args.min_confidence,
        min_note_frames=args.min_note_frames,
        merge_gap_frames=args.merge_gap_frames,
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
