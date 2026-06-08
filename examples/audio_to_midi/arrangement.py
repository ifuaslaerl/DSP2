from dataclasses import dataclass


@dataclass(frozen=True)
class PitchCandidate:
    frame: int
    midi_note: int
    salience: float


@dataclass(frozen=True)
class NoteEvent:
    pitch: int
    start_frame: int
    end_frame: int
    confidence: float


@dataclass(frozen=True)
class MotorVoice:
    channel: int
    events: tuple


def duration_ms_to_frames(duration_ms, hop_size, sample_rate, allow_zero=False):
    if duration_ms is None:
        return None
    if hop_size <= 0:
        raise ValueError("hop_size deve ser positivo.")
    if sample_rate <= 0:
        raise ValueError("sample_rate deve ser positivo.")
    if duration_ms < 0.0 or (duration_ms == 0.0 and not allow_zero):
        raise ValueError("duracao em ms deve ser positiva.")

    if duration_ms == 0.0:
        return 0

    frame_ms = 1000.0 * float(hop_size) / float(sample_rate)
    return max(1, int((float(duration_ms) + frame_ms - 1e-9) // frame_ms))


def candidates_to_frame_tuples(candidate_frames, min_midi_note, max_midi_note):
    frames = []
    for frame in candidate_frames:
        filtered = []
        for candidate in frame:
            midi_note = int(round(candidate.midi_note))
            if min_midi_note <= midi_note <= max_midi_note and candidate.salience > 0.0:
                filtered.append((midi_note, float(candidate.salience)))
        frames.append(filtered)
    return frames


def note_frames_to_events(note_frames, candidate_frames=None):
    events = []
    index = 0
    while index < len(note_frames):
        frame = note_frames[index]
        note = int(round(frame[0])) if frame else 0
        if note <= 0:
            index += 1
            continue

        end = index + 1
        while end < len(note_frames):
            next_frame = note_frames[end]
            next_note = int(round(next_frame[0])) if next_frame else 0
            if next_note != note:
                break
            end += 1

        confidence_values = []
        if candidate_frames is not None:
            for frame_index in range(index, end):
                for candidate in candidate_frames[frame_index]:
                    if int(round(candidate.midi_note)) == note:
                        confidence_values.append(max(0.0, min(1.0, float(candidate.salience))))
                        break

        confidence = (
            sum(confidence_values) / float(len(confidence_values))
            if confidence_values
            else 1.0
        )
        events.append(NoteEvent(note, index, end, confidence))
        index = end

    return events


def events_to_note_frames(events, frame_count):
    frames = [[] for _ in range(frame_count)]
    for event in events:
        start = max(0, int(event.start_frame))
        end = min(frame_count, int(event.end_frame))
        for frame_index in range(start, end):
            frames[frame_index] = [int(event.pitch)]
    return frames


def _event_pitch_at(events, frame_index):
    for event in events:
        if event.start_frame <= frame_index < event.end_frame:
            return event.pitch
    return 0


def _voice_frames_to_events(channel, voice_frames):
    note_frames = [[note] if note > 0 else [] for note in voice_frames]
    return MotorVoice(channel, tuple(note_frames_to_events(note_frames)))


def _triad_candidates(melody_note, min_midi_note, max_midi_note):
    pitch_classes = {
        melody_note % 12,
        (melody_note + 3) % 12,
        (melody_note + 4) % 12,
        (melody_note + 7) % 12,
        (melody_note + 10) % 12,
    }
    notes = []
    for note in range(min_midi_note, max_midi_note + 1):
        if note % 12 in pitch_classes and note != melody_note:
            notes.append(note)
    notes.sort(key=lambda note: (abs(note - melody_note), note))
    return notes


def arrange_for_motors(
    melody_events,
    bass_events=None,
    mode="melody_only",
    frame_count=None,
    motor_count=6,
    harmony_min_midi_note=40,
    harmony_max_midi_note=76,
    harmony_confidence=0.55,
    stable_note_frames=4,
):
    if motor_count < 1 or motor_count > 6:
        raise ValueError("motor_count deve estar entre 1 e 6.")
    if mode not in {"melody_only", "melody_bass", "recognizable_orchestra_v2"}:
        raise ValueError(
            "mode deve ser 'melody_only', 'melody_bass' ou 'recognizable_orchestra_v2'."
        )

    bass_events = bass_events or []
    all_events = list(melody_events) + list(bass_events)
    if frame_count is None:
        frame_count = max((event.end_frame for event in all_events), default=0)

    channel_frames = [[0 for _ in range(frame_count)] for _ in range(motor_count)]

    for event in melody_events:
        if motor_count < 1:
            break
        for frame_index in range(max(0, event.start_frame), min(frame_count, event.end_frame)):
            channel_frames[0][frame_index] = event.pitch

    if mode in {"melody_bass", "recognizable_orchestra_v2"} and motor_count >= 2:
        for event in bass_events:
            if event.pitch < 32 or event.pitch > 55:
                continue
            for frame_index in range(max(0, event.start_frame), min(frame_count, event.end_frame)):
                channel_frames[1][frame_index] = event.pitch

    if mode == "recognizable_orchestra_v2" and motor_count >= 3:
        for event in melody_events:
            if event.confidence < harmony_confidence:
                continue
            if event.end_frame - event.start_frame < stable_note_frames:
                continue

            candidates = _triad_candidates(
                event.pitch,
                harmony_min_midi_note,
                harmony_max_midi_note,
            )
            extra_notes = []
            for note in candidates:
                if len(extra_notes) >= min(2, motor_count - 2):
                    break
                if abs(note - event.pitch) < 3:
                    continue
                extra_notes.append(note)

            for extra_index, note in enumerate(extra_notes):
                channel_index = 2 + extra_index
                for frame_index in range(max(0, event.start_frame), min(frame_count, event.end_frame)):
                    if _event_pitch_at(bass_events, frame_index) == note:
                        continue
                    channel_frames[channel_index][frame_index] = note

    voices = tuple(
        _voice_frames_to_events(channel + 1, channel_frames[channel])
        for channel in range(motor_count)
    )
    frames = []
    for frame_index in range(frame_count):
        frame = []
        for channel in range(motor_count):
            frame.append(channel_frames[channel][frame_index])
        frames.append(frame)

    return voices, frames
