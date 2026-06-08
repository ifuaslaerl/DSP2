import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

# Injeta a raiz do projeto no path para que o script possa importar o dsp2 de qualquer lugar
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import dsp2._dsp2_core as core
from dsp2.signal_io import load_pcm_timeseries_data
from dsp2.graph_loader import GraphLoader
from examples.audio_to_midi.arrangement import (
    PitchCandidate,
    arrange_for_motors,
    candidates_to_frame_tuples,
    duration_ms_to_frames,
    note_frames_to_events,
)
from examples.audio_to_midi.midi_io import write_midi_file  # Import local do módulo que movemos junto

NOTE_NAME_TO_PITCH_CLASS = {
    "C": 0,
    "C#": 1,
    "DB": 1,
    "D": 2,
    "D#": 3,
    "EB": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "GB": 6,
    "G": 7,
    "G#": 8,
    "AB": 8,
    "A": 9,
    "A#": 10,
    "BB": 10,
    "B": 11,
}

SCALE_INTERVALS = {
    "major": (0, 2, 4, 5, 7, 9, 11),
    "minor": (0, 2, 3, 5, 7, 8, 10),
    "natural_minor": (0, 2, 3, 5, 7, 8, 10),
}

RECOGNIZABLE_ORCHESTRA_PROFILE = {
    "mode": "harmony",
    "motor_mode": "voices",
    "motor_count": 6,
    "block_size": 2048,
    "fft_size": 4096,
    "hop_size": 1024,
    "min_midi_note": 32,
    "max_midi_note": 83,
    "relative_threshold": 0.08,
    "min_confidence": 0.20,
    "min_note_frames": 8,
    "merge_gap_frames": 3,
    "path_candidate_count": 5,
    "harmony_voices": 6,
    "jump_penalty": 0.10,
    "octave_jump_penalty": 0.70,
    "silence_transition_penalty": 0.10,
}

RECOGNIZABLE_ORCHESTRA_V2_PROFILE = {
    "mode": "recognizable_orchestra_v2",
    "motor_mode": "voices",
    "motor_count": 6,
    "block_size": 2048,
    "fft_size": 4096,
    "hop_size": 1024,
    "min_midi_note": 55,
    "max_midi_note": 83,
    "relative_threshold": 0.08,
    "min_confidence": 0.20,
    "min_note_ms": 100.0,
    "merge_gap_ms": 70.0,
    "path_candidate_count": 5,
    "harmony_voices": 4,
    "jump_penalty": 0.10,
    "octave_jump_penalty": 0.70,
    "silence_transition_penalty": 0.10,
}

PROFILES = {
    "recognizable-orchestra": RECOGNIZABLE_ORCHESTRA_PROFILE,
    "recognizable-orchestra-v2": RECOGNIZABLE_ORCHESTRA_V2_PROFILE,
}

LEGACY_MODES = {"peaks", "melody", "harmony"}
ARRANGEMENT_MODES = {"melody_only", "melody_bass", "recognizable_orchestra_v2"}
VALID_MODES = LEGACY_MODES | ARRANGEMENT_MODES


def _normalise_profile(profile):
    if profile is None:
        return None
    normalised = profile.strip().lower()
    if normalised not in PROFILES:
        raise ValueError(
            "profile deve ser 'recognizable-orchestra' ou 'recognizable-orchestra-v2'."
        )
    return normalised


def get_profile_parameters(profile):
    normalised = _normalise_profile(profile)
    if normalised is None:
        return {}
    return dict(PROFILES[normalised])


def convert_to_analysis_wav(input_path, output_path):
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        raise RuntimeError(
            "ffmpeg nao encontrado. Recrie o container com "
            "`docker compose up -d --build` para converter MP3/OGG para WAV."
        )

    command = [
        ffmpeg_path,
        "-y",
        "-i",
        input_path,
        "-ac",
        "1",
        "-ar",
        "44100",
        "-sample_fmt",
        "s16",
        output_path,
    ]
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip()
        if stderr:
            raise RuntimeError(f"ffmpeg falhou ao converter o audio: {stderr}") from exc
        raise RuntimeError("ffmpeg falhou ao converter o audio.") from exc


def resolve_analysis_audio_path(input_path, workspace_dir):
    extension = os.path.splitext(input_path)[1].lower()
    if extension == ".wav":
        return input_path, False

    converted_path = os.path.join(workspace_dir, "analysis_input.wav")
    convert_to_analysis_wav(input_path, converted_path)
    return converted_path, True


def build_audio_to_midi_graph(
    path,
    input_path,
    fft_size,
    peak_count,
    threshold,
    min_frequency,
    max_frequency,
    min_bin_distance,
    mode="melody",
    hop_size=None,
    min_midi_note=36,
    max_midi_note=84,
    harmonic_count=6,
    relative_threshold=0.05,
    min_confidence=0.2,
    path_candidate_count=5,
):
    if mode not in VALID_MODES:
        raise ValueError(
            "mode deve ser 'peaks', 'melody', 'harmony', 'melody_only', "
            "'melody_bass' ou 'recognizable_orchestra_v2'."
        )

    audio_parameters = {"path": input_path}
    if hop_size is not None:
        audio_parameters["hop_size"] = hop_size

    nodes = [
        {
            "name": "Audio",
            "type": "FileSignalInput",
            "parameters": audio_parameters,
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
                        "path_candidate_count": path_candidate_count,
                    },
                },
                {
                    "name": "Midi",
                    "type": "FrequencyToMidiNote",
                },
                {
                    "name": "MidiCandidates",
                    "type": "FrequencyToMidiNote",
                },
            ]
        )
        edges.extend(
            [
                {"source": "Spectrum", "source_port": 0, "dest": "Pitch", "dest_port": 0},
                {"source": "Spectrum", "source_port": 1, "dest": "Pitch", "dest_port": 1},
                {"source": "Pitch", "source_port": 0, "dest": "Midi", "dest_port": 0},
                {"source": "Pitch", "source_port": 2, "dest": "MidiCandidates", "dest_port": 0},
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
    hop_size,
    path_candidate_count,
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
    if mode not in VALID_MODES:
        raise ValueError(
            "mode deve ser 'peaks', 'melody', 'harmony', 'melody_only', "
            "'melody_bass' ou 'recognizable_orchestra_v2'."
        )
    if min_midi_note < 0 or max_midi_note > 127 or max_midi_note < min_midi_note:
        raise ValueError("faixa MIDI deve estar entre 0..127 e ser crescente.")
    if harmonic_count <= 0:
        raise ValueError("harmonic_count deve ser positivo.")
    if relative_threshold < 0.0:
        raise ValueError("relative_threshold nao pode ser negativo.")
    if min_confidence < 0.0:
        raise ValueError("min_confidence nao pode ser negativo.")
    if hop_size <= 0:
        raise ValueError("hop_size deve ser positivo.")
    if path_candidate_count <= 0:
        raise ValueError("path_candidate_count deve ser positivo.")


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


def select_melody_path(
    candidate_frames,
    jump_penalty=0.04,
    octave_jump_penalty=0.25,
    silence_transition_penalty=0.10,
):
    """Escolhe offline o contorno melodico mais estavel entre candidatos por frame."""
    if jump_penalty < 0.0 or octave_jump_penalty < 0.0 or silence_transition_penalty < 0.0:
        raise ValueError("penalidades do caminho melodico nao podem ser negativas.")
    if not candidate_frames:
        return []

    states_by_frame = []
    for frame in candidate_frames:
        best_salience_by_note = {}
        for note, salience in frame:
            midi_note = _clamp_note(int(round(note)), 0, 127)
            normalised_salience = max(0.0, min(1.0, float(salience)))
            if midi_note > 0 and normalised_salience > best_salience_by_note.get(midi_note, 0.0):
                best_salience_by_note[midi_note] = normalised_salience
        states_by_frame.append([(0, 0.0)] + sorted(best_salience_by_note.items()))

    def transition_cost(previous_note, current_note):
        if previous_note == current_note:
            return 0.0
        if previous_note == 0 or current_note == 0:
            return silence_transition_penalty

        interval = abs(previous_note - current_note)
        cost = interval * jump_penalty
        if interval >= 12:
            cost += octave_jump_penalty
        return cost

    previous_scores = [salience for _, salience in states_by_frame[0]]
    backtrack = []
    for frame_index in range(1, len(states_by_frame)):
        previous_states = states_by_frame[frame_index - 1]
        current_states = states_by_frame[frame_index]
        current_scores = []
        current_backtrack = []

        for current_note, salience in current_states:
            best_previous = 0
            best_score = previous_scores[0] - transition_cost(previous_states[0][0], current_note)
            for previous_index in range(1, len(previous_states)):
                score = previous_scores[previous_index] - transition_cost(
                    previous_states[previous_index][0],
                    current_note,
                )
                if score > best_score:
                    best_previous = previous_index
                    best_score = score
            current_scores.append(best_score + salience)
            current_backtrack.append(best_previous)

        previous_scores = current_scores
        backtrack.append(current_backtrack)

    selected_index = max(range(len(previous_scores)), key=previous_scores.__getitem__)
    selected_notes = [states_by_frame[-1][selected_index][0]]
    for frame_index in range(len(states_by_frame) - 1, 0, -1):
        selected_index = backtrack[frame_index - 1][selected_index]
        selected_notes.append(states_by_frame[frame_index - 1][selected_index][0])
    selected_notes.reverse()

    return [[note] if note > 0 else [] for note in selected_notes]


def _validate_motor_count(motor_count):
    if (
        not isinstance(motor_count, int)
        or isinstance(motor_count, bool)
        or motor_count < 1
        or motor_count > 6
    ):
        raise ValueError("motor_count deve estar entre 1 e 6.")


def _normalise_harmony_key(harmony_key):
    key = harmony_key.strip().upper()
    if key not in NOTE_NAME_TO_PITCH_CLASS:
        raise ValueError("harmony_key deve ser uma nota entre C, C#, Db ... B.")
    return NOTE_NAME_TO_PITCH_CLASS[key]


def _normalise_harmony_scale(harmony_scale):
    scale = harmony_scale.strip().lower().replace("-", "_")
    if scale not in SCALE_INTERVALS:
        raise ValueError("harmony_scale deve ser 'major' ou 'minor'.")
    return SCALE_INTERVALS[scale]


def _pitch_class_distance(left, right):
    distance = abs(left - right) % 12
    return min(distance, 12 - distance)


def _nearest_scale_degree(pitch_class, scale_pitch_classes):
    return min(
        range(len(scale_pitch_classes)),
        key=lambda degree: (_pitch_class_distance(pitch_class, scale_pitch_classes[degree]), degree),
    )


def _midi_notes_for_pitch_classes(pitch_classes, min_midi_note, max_midi_note):
    notes = []
    allowed = set(pitch_classes)
    for note in range(min_midi_note, max_midi_note + 1):
        if note % 12 in allowed:
            notes.append(note)
    return notes


def harmonize_note_frames(
    frames,
    harmony_key="D",
    harmony_scale="minor",
    harmony_voices=6,
    min_midi_note=36,
    max_midi_note=84,
):
    if harmony_voices <= 0:
        raise ValueError("harmony_voices deve ser positivo.")
    if min_midi_note < 0 or max_midi_note > 127 or max_midi_note < min_midi_note:
        raise ValueError("faixa MIDI deve estar entre 0..127 e ser crescente.")

    root_pitch_class = _normalise_harmony_key(harmony_key)
    scale_intervals = _normalise_harmony_scale(harmony_scale)
    scale_pitch_classes = tuple((root_pitch_class + interval) % 12 for interval in scale_intervals)

    harmonized = []
    for frame in frames:
        if not frame:
            harmonized.append([])
            continue

        melody_note = _clamp_note(int(round(frame[0])), min_midi_note, max_midi_note)
        degree = _nearest_scale_degree(melody_note % 12, scale_pitch_classes)
        triad_pitch_classes = (
            scale_pitch_classes[degree],
            scale_pitch_classes[(degree + 2) % len(scale_pitch_classes)],
            scale_pitch_classes[(degree + 4) % len(scale_pitch_classes)],
        )
        candidates = _midi_notes_for_pitch_classes(
            triad_pitch_classes,
            min_midi_note,
            max_midi_note,
        )
        candidates.sort(key=lambda note: (abs(note - melody_note), note))

        voices = [melody_note]
        used_notes = {melody_note}
        for note in candidates:
            if len(voices) >= harmony_voices:
                break
            if note not in used_notes:
                voices.append(note)
                used_notes.add(note)

        harmonized.append(voices)

    return harmonized


def analyze_audio(
    input_path,
    block_size=2048,
    fft_size=None,
    hop_size=None,
    peak_count=6,
    threshold=0.001,
    min_frequency=20.0,
    max_frequency=None,
    min_bin_distance=2,
    mode="melody",
    min_midi_note=36,
    max_midi_note=84,
    harmonic_count=6,
    relative_threshold=0.05,
    min_confidence=0.2,
    path_candidate_count=5,
):
    if fft_size is None:
        fft_size = block_size
    if hop_size is None:
        hop_size = block_size if mode == "peaks" else max(1, block_size // 4)

    graph_mode = "peaks" if mode == "peaks" else "melody"
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
        hop_size,
        path_candidate_count,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        analysis_input_path, converted_input = resolve_analysis_audio_path(input_path, tmpdir)
        samples, sample_rate = load_pcm_timeseries_data(analysis_input_path)
        block_count = max(1, int(math.ceil(len(samples) / float(hop_size))))

        graph_path = os.path.join(tmpdir, "audio_to_midi_graph.json")
        build_audio_to_midi_graph(
            graph_path,
            os.path.abspath(analysis_input_path),
            fft_size,
            peak_count,
            threshold,
            min_frequency,
            max_frequency,
            min_bin_distance,
            mode=graph_mode,
            hop_size=hop_size,
            min_midi_note=min_midi_note,
            max_midi_note=max_midi_note,
            harmonic_count=harmonic_count,
            relative_threshold=relative_threshold,
            min_confidence=min_confidence,
            path_candidate_count=path_candidate_count,
        )

        engine = core.Engine()
        engine.set_signal_parameters(float(sample_rate), block_size)
        node_ids = GraphLoader.load_from_json(engine, graph_path)
        core.get_logs()
        engine.prepare_engine()

        frames = []
        candidate_frames = []
        for frame_index in range(block_count):
            engine.process_block()
            if graph_mode == "peaks":
                notes = engine.get_node_output(node_ids["Midi"], 0)
                frames.append([int(round(note)) for note in notes if int(round(note)) > 0])
            else:
                notes = engine.get_node_output(node_ids["MidiCandidates"], 0)
                saliences = engine.get_node_output(node_ids["Pitch"], 3)
                candidate_frames.append(
                    [
                        PitchCandidate(frame_index, int(round(note)), float(salience))
                        for note, salience in zip(notes, saliences)
                        if int(round(note)) > 0 and salience > 0.0
                    ]
                )

        logs = core.get_logs()

    return {
        "frames": frames,
        "candidate_frames": candidate_frames,
        "sample_rate": sample_rate,
        "sample_count": len(samples),
        "block_count": block_count,
        "hop_size": hop_size,
        "logs": logs,
        "mode": mode,
        "converted_input": converted_input,
    }


def _filter_candidate_frames(candidate_frames, min_midi_note, max_midi_note):
    return [
        [
            candidate
            for candidate in frame
            if min_midi_note <= int(round(candidate.midi_note)) <= max_midi_note
        ]
        for frame in candidate_frames
    ]


def _extract_note_events(
    candidate_frames,
    min_midi_note,
    max_midi_note,
    min_note_frames,
    merge_gap_frames,
    jump_penalty=0.04,
    octave_jump_penalty=0.25,
    silence_transition_penalty=0.10,
):
    filtered_candidates = _filter_candidate_frames(
        candidate_frames,
        min_midi_note,
        max_midi_note,
    )
    selected_frames = select_melody_path(
        candidates_to_frame_tuples(filtered_candidates, min_midi_note, max_midi_note),
        jump_penalty=jump_penalty,
        octave_jump_penalty=octave_jump_penalty,
        silence_transition_penalty=silence_transition_penalty,
    )
    processed_frames = postprocess_note_frames(
        selected_frames,
        min_midi_note=min_midi_note,
        max_midi_note=max_midi_note,
        min_note_frames=min_note_frames,
        merge_gap_frames=merge_gap_frames,
    )
    return note_frames_to_events(processed_frames, filtered_candidates), processed_frames


def extract_melody(
    candidate_frames,
    min_note_frames,
    merge_gap_frames,
    min_midi_note=55,
    max_midi_note=83,
    jump_penalty=0.04,
    octave_jump_penalty=0.25,
    silence_transition_penalty=0.10,
):
    return _extract_note_events(
        candidate_frames,
        min_midi_note,
        max_midi_note,
        min_note_frames,
        merge_gap_frames,
        jump_penalty=jump_penalty,
        octave_jump_penalty=octave_jump_penalty,
        silence_transition_penalty=silence_transition_penalty,
    )


def extract_bass(
    candidate_frames,
    min_note_frames,
    merge_gap_frames,
    min_midi_note=32,
    max_midi_note=55,
    jump_penalty=0.04,
    octave_jump_penalty=0.25,
    silence_transition_penalty=0.10,
):
    return _extract_note_events(
        candidate_frames,
        min_midi_note,
        max_midi_note,
        min_note_frames,
        merge_gap_frames,
        jump_penalty=jump_penalty,
        octave_jump_penalty=octave_jump_penalty,
        silence_transition_penalty=silence_transition_penalty,
    )


def _duration_frames_for_arrangement(min_note_ms, merge_gap_ms, hop_size, sample_rate):
    min_note = 100.0 if min_note_ms is None else min_note_ms
    merge_gap = 70.0 if merge_gap_ms is None else merge_gap_ms
    return (
        duration_ms_to_frames(min_note, hop_size, sample_rate),
        duration_ms_to_frames(merge_gap, hop_size, sample_rate, allow_zero=True),
    )


def collect_midi_note_frames(
    input_path,
    block_size=2048,
    fft_size=None,
    hop_size=None,
    peak_count=6,
    threshold=0.001,
    min_frequency=20.0,
    max_frequency=None,
    min_bin_distance=2,
    mode="melody",
    min_midi_note=36,
    max_midi_note=84,
    harmonic_count=6,
    relative_threshold=0.05,
    min_confidence=0.2,
    path_candidate_count=5,
    min_note_frames=2,
    merge_gap_frames=1,
    min_note_ms=None,
    merge_gap_ms=None,
    harmony_key="D",
    harmony_scale="minor",
    harmony_voices=6,
    motor_count=6,
    jump_penalty=0.04,
    octave_jump_penalty=0.25,
    silence_transition_penalty=0.10,
):
    if fft_size is None:
        fft_size = block_size
    if hop_size is None:
        hop_size = block_size if mode == "peaks" else max(1, block_size // 4)
    _validate_motor_count(motor_count)

    if mode in LEGACY_MODES:
        capture = analyze_audio(
            input_path,
            block_size=block_size,
            fft_size=fft_size,
            hop_size=hop_size,
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
            path_candidate_count=path_candidate_count,
        )

        frames = capture["frames"]
        if mode in {"melody", "harmony"}:
            frames = select_melody_path(
                candidates_to_frame_tuples(
                    capture["candidate_frames"],
                    min_midi_note,
                    max_midi_note,
                ),
                jump_penalty=jump_penalty,
                octave_jump_penalty=octave_jump_penalty,
                silence_transition_penalty=silence_transition_penalty,
            )
            frames = postprocess_note_frames(
                frames,
                min_midi_note=min_midi_note,
                max_midi_note=max_midi_note,
                min_note_frames=min_note_frames,
                merge_gap_frames=merge_gap_frames,
            )
        if mode == "harmony":
            frames = harmonize_note_frames(
                frames,
                harmony_key=harmony_key,
                harmony_scale=harmony_scale,
                harmony_voices=min(harmony_voices, motor_count),
                min_midi_note=min_midi_note,
                max_midi_note=max_midi_note,
            )

        capture["frames"] = frames
        return capture

    melody_capture = analyze_audio(
        input_path,
        block_size=block_size,
        fft_size=fft_size,
        hop_size=hop_size,
        peak_count=peak_count,
        threshold=threshold,
        min_frequency=min_frequency,
        max_frequency=max_frequency,
        min_bin_distance=min_bin_distance,
        mode=mode,
        min_midi_note=55,
        max_midi_note=83,
        harmonic_count=harmonic_count,
        relative_threshold=relative_threshold,
        min_confidence=min_confidence,
        path_candidate_count=path_candidate_count,
    )
    min_frames, merge_frames = _duration_frames_for_arrangement(
        min_note_ms,
        merge_gap_ms,
        melody_capture["hop_size"],
        melody_capture["sample_rate"],
    )
    melody_events, _ = extract_melody(
        melody_capture["candidate_frames"],
        min_frames,
        merge_frames,
        min_midi_note=55,
        max_midi_note=83,
        jump_penalty=jump_penalty,
        octave_jump_penalty=octave_jump_penalty,
        silence_transition_penalty=silence_transition_penalty,
    )

    bass_events = []
    logs = list(melody_capture["logs"])
    converted_input = melody_capture["converted_input"]
    if mode in {"melody_bass", "recognizable_orchestra_v2"}:
        bass_capture = analyze_audio(
            input_path,
            block_size=block_size,
            fft_size=fft_size,
            hop_size=hop_size,
            peak_count=peak_count,
            threshold=threshold,
            min_frequency=min_frequency,
            max_frequency=max_frequency,
            min_bin_distance=min_bin_distance,
            mode=mode,
            min_midi_note=32,
            max_midi_note=55,
            harmonic_count=harmonic_count,
            relative_threshold=relative_threshold,
            min_confidence=min_confidence,
            path_candidate_count=path_candidate_count,
        )
        bass_events, _ = extract_bass(
            bass_capture["candidate_frames"],
            min_frames,
            merge_frames,
            min_midi_note=32,
            max_midi_note=55,
            jump_penalty=jump_penalty,
            octave_jump_penalty=octave_jump_penalty,
            silence_transition_penalty=silence_transition_penalty,
        )
        logs.extend(bass_capture["logs"])
        converted_input = converted_input or bass_capture["converted_input"]

    voices, frames = arrange_for_motors(
        melody_events,
        bass_events=bass_events,
        mode=mode,
        frame_count=melody_capture["block_count"],
        motor_count=motor_count,
        harmony_min_midi_note=40,
        harmony_max_midi_note=76,
        harmony_confidence=max(0.55, min_confidence + 0.20),
        stable_note_frames=max(min_frames, 4),
    )
    melody_capture["frames"] = frames
    melody_capture["voices"] = voices
    melody_capture["logs"] = logs
    melody_capture["mode"] = mode
    melody_capture["converted_input"] = converted_input
    melody_capture["min_note_frames"] = min_frames
    melody_capture["merge_gap_frames"] = merge_frames
    return melody_capture


def export_audio_to_midi(
    input_path,
    output_path,
    block_size=2048,
    fft_size=None,
    hop_size=None,
    peak_count=6,
    threshold=0.001,
    min_frequency=20.0,
    max_frequency=None,
    min_bin_distance=2,
    tempo_bpm=120.0,
    velocity=96,
    program=0,
    ppq=480,
    mode="melody",
    motor_mode=None,
    motor_count=6,
    min_midi_note=36,
    max_midi_note=84,
    harmonic_count=6,
    relative_threshold=0.05,
    min_confidence=0.2,
    path_candidate_count=5,
    min_note_frames=2,
    merge_gap_frames=1,
    min_note_ms=None,
    merge_gap_ms=None,
    harmony_key="D",
    harmony_scale="minor",
    harmony_voices=6,
    jump_penalty=0.04,
    octave_jump_penalty=0.25,
    silence_transition_penalty=0.10,
    profile=None,
):
    if profile is not None:
        profile_parameters = get_profile_parameters(profile)
        mode = profile_parameters["mode"]
        motor_mode = profile_parameters["motor_mode"]
        motor_count = profile_parameters["motor_count"]
        block_size = profile_parameters["block_size"]
        fft_size = profile_parameters["fft_size"]
        hop_size = profile_parameters["hop_size"]
        min_midi_note = profile_parameters["min_midi_note"]
        max_midi_note = profile_parameters["max_midi_note"]
        relative_threshold = profile_parameters["relative_threshold"]
        min_confidence = profile_parameters["min_confidence"]
        min_note_frames = profile_parameters.get("min_note_frames", min_note_frames)
        merge_gap_frames = profile_parameters.get("merge_gap_frames", merge_gap_frames)
        min_note_ms = profile_parameters.get("min_note_ms", min_note_ms)
        merge_gap_ms = profile_parameters.get("merge_gap_ms", merge_gap_ms)
        path_candidate_count = profile_parameters["path_candidate_count"]
        harmony_voices = profile_parameters["harmony_voices"]
        jump_penalty = profile_parameters["jump_penalty"]
        octave_jump_penalty = profile_parameters["octave_jump_penalty"]
        silence_transition_penalty = profile_parameters["silence_transition_penalty"]

    if tempo_bpm <= 0.0:
        raise ValueError("tempo_bpm deve ser positivo.")
    if ppq <= 0:
        raise ValueError("ppq deve ser positivo.")
    _validate_motor_count(motor_count)

    capture = collect_midi_note_frames(
        input_path,
        block_size=block_size,
        fft_size=fft_size,
        hop_size=hop_size,
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
        path_candidate_count=path_candidate_count,
        min_note_frames=min_note_frames,
        merge_gap_frames=merge_gap_frames,
        min_note_ms=min_note_ms,
        merge_gap_ms=merge_gap_ms,
        harmony_key=harmony_key,
        harmony_scale=harmony_scale,
        harmony_voices=harmony_voices,
        motor_count=motor_count,
        jump_penalty=jump_penalty,
        octave_jump_penalty=octave_jump_penalty,
        silence_transition_penalty=silence_transition_penalty,
    )

    ticks_per_second = ppq * (tempo_bpm / 60.0)
    frame_seconds = capture["hop_size"] / float(capture["sample_rate"])
    frame_ticks = max(1, int(round(frame_seconds * ticks_per_second)))

    midi_info = write_midi_file(
        output_path,
        capture["frames"],
        frame_ticks,
        tempo_bpm=tempo_bpm,
        velocity=velocity,
        program=program,
        ppq=ppq,
        motor_mode=motor_mode or ("voices" if mode in {"harmony"} | ARRANGEMENT_MODES else "single"),
        channels=range(1, motor_count + 1),
    )

    capture["motor_count"] = motor_count
    capture.update(midi_info)
    return capture


def _explicit_cli_dests(parser, argv):
    option_to_dest = {}
    for action in parser._actions:
        for option in action.option_strings:
            option_to_dest[option] = action.dest

    explicit = set()
    for token in argv:
        if not token.startswith("--"):
            continue
        option = token.split("=", 1)[0]
        if option in option_to_dest:
            explicit.add(option_to_dest[option])
    return explicit


def apply_profile_to_args(args, explicit_dests):
    if args.profile is None:
        return

    for name, value in get_profile_parameters(args.profile).items():
        if name not in explicit_dests:
            setattr(args, name, value)


def main():
    parser = argparse.ArgumentParser(description="Exporta um WAV para MIDI usando o pipeline DSP2.")
    parser.add_argument("--input", required=True, help="Arquivo WAV PCM ou audio compativel com ffmpeg.")
    parser.add_argument("--output", default="dev_panel/outputs/export.mid", help="Arquivo .mid de saida.")    
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES.keys()),
        default=None,
        help="Preset reproduzivel de conversao. Use recognizable-orchestra-v2 para o arranjo recomendado.",
    )
    parser.add_argument("--block-size", type=int, default=2048, help="Tamanho de bloco de analise.")
    parser.add_argument("--fft-size", type=int, default=None, help="Tamanho da FFT; default igual ao block-size.")
    parser.add_argument("--hop-size", type=int, default=None, help="Avanco entre janelas; default block-size/4 no modo melody.")
    parser.add_argument("--peak-count", type=int, default=6, help="Numero maximo de notas simultaneas por bloco.")
    parser.add_argument("--threshold", type=float, default=0.001, help="Limiar minimo de potencia espectral.")
    parser.add_argument("--min-frequency", type=float, default=20.0, help="Menor frequencia analisada em Hz.")
    parser.add_argument("--max-frequency", type=float, default=None, help="Maior frequencia analisada em Hz.")
    parser.add_argument("--min-bin-distance", type=int, default=2, help="Distancia minima entre picos espectrais.")
    parser.add_argument("--mode", choices=sorted(VALID_MODES), default="melody", help="Modo de transcricao.")
    parser.add_argument(
        "--motor-mode",
        choices=["single", "unison", "round-robin", "voices"],
        default=None,
        help="Distribuicao das notas nos motores MIDI 1..6.",
    )
    parser.add_argument("--motor-count", type=int, default=6, help="Limite de motores/canais MIDI, entre 1 e 6.")
    parser.add_argument("--min-midi-note", type=int, default=36, help="Menor nota MIDI no modo melody.")
    parser.add_argument("--max-midi-note", type=int, default=84, help="Maior nota MIDI no modo melody.")
    parser.add_argument("--harmonic-count", type=int, default=6, help="Numero de harmonicos no modo melody.")
    parser.add_argument("--relative-threshold", type=float, default=0.05, help="Limiar relativo no modo melody.")
    parser.add_argument("--min-confidence", type=float, default=0.2, help="Confianca minima no modo melody.")
    parser.add_argument("--path-candidate-count", type=int, default=5, help="Candidatos por janela para estabilizacao melodica offline.")
    parser.add_argument("--min-note-frames", type=int, default=2, help="Duracao minima em blocos no modo melody.")
    parser.add_argument("--merge-gap-frames", type=int, default=1, help="Lacuna maxima para unir notas iguais.")
    parser.add_argument("--min-note-ms", type=float, default=None, help="Duracao minima em ms nos modos novos.")
    parser.add_argument("--merge-gap-ms", type=float, default=None, help="Lacuna maxima em ms nos modos novos.")
    parser.add_argument("--harmony-key", default="D", help="Tonalidade do modo harmony.")
    parser.add_argument("--harmony-scale", default="minor", help="Escala do modo harmony: major ou minor.")
    parser.add_argument("--harmony-voices", type=int, default=6, help="Numero maximo de vozes no modo harmony.")
    parser.add_argument("--jump-penalty", type=float, default=0.04, help="Penalidade por salto melodico entre janelas.")
    parser.add_argument("--octave-jump-penalty", type=float, default=0.25, help="Penalidade extra para saltos de oitava ou maiores.")
    parser.add_argument("--silence-transition-penalty", type=float, default=0.10, help="Penalidade para entrar ou sair de silencio.")
    parser.add_argument("--tempo-bpm", type=float, default=120.0, help="Tempo do arquivo MIDI exportado.")
    parser.add_argument("--velocity", type=int, default=96, help="Velocidade MIDI das notas.")
    parser.add_argument("--program", type=int, default=0, help="Program change MIDI, default piano acustico.")
    parser.add_argument("--ppq", type=int, default=480, help="Pulsos MIDI por seminima.")

    explicit_dests = _explicit_cli_dests(parser, sys.argv[1:])
    args = parser.parse_args()
    apply_profile_to_args(args, explicit_dests)
    result = export_audio_to_midi(
        args.input,
        args.output,
        block_size=args.block_size,
        fft_size=args.fft_size,
        hop_size=args.hop_size,
        peak_count=args.peak_count,
        threshold=args.threshold,
        min_frequency=args.min_frequency,
        max_frequency=args.max_frequency,
        min_bin_distance=args.min_bin_distance,
        mode=args.mode,
        motor_mode=args.motor_mode,
        motor_count=args.motor_count,
        min_midi_note=args.min_midi_note,
        max_midi_note=args.max_midi_note,
        harmonic_count=args.harmonic_count,
        relative_threshold=args.relative_threshold,
        min_confidence=args.min_confidence,
        path_candidate_count=args.path_candidate_count,
        min_note_frames=args.min_note_frames,
        merge_gap_frames=args.merge_gap_frames,
        min_note_ms=args.min_note_ms,
        merge_gap_ms=args.merge_gap_ms,
        harmony_key=args.harmony_key,
        harmony_scale=args.harmony_scale,
        harmony_voices=args.harmony_voices,
        jump_penalty=args.jump_penalty,
        octave_jump_penalty=args.octave_jump_penalty,
        silence_transition_penalty=args.silence_transition_penalty,
        tempo_bpm=args.tempo_bpm,
        velocity=args.velocity,
        program=args.program,
        ppq=args.ppq,
    )

    unique_notes = sorted({note for frame in result["frames"] for note in frame if note > 0})
    print(f"MIDI gerado: {args.output}")
    if args.profile:
        print(f"Profile usado: {args.profile}")
    if result["converted_input"]:
        print("Entrada convertida para WAV PCM temporario antes da analise.")
    print(f"Blocos processados: {result['block_count']}")
    print(f"Notas detectadas: {unique_notes}")
    if result["logs"]:
        print(f"Logs C++ coletados: {len(result['logs'])}")


if __name__ == "__main__":
    main()
