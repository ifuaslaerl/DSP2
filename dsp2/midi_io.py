import os
import struct


def encode_variable_length_quantity(value):
    if value < 0:
        raise ValueError("VLQ MIDI nao pode codificar valores negativos.")

    buffer = value & 0x7F
    value >>= 7
    while value:
        buffer <<= 8
        buffer |= ((value & 0x7F) | 0x80)
        value >>= 7

    encoded = bytearray()
    while True:
        encoded.append(buffer & 0xFF)
        if buffer & 0x80:
            buffer >>= 8
        else:
            break

    return bytes(encoded)


def _clamp_int(value, minimum, maximum):
    rounded = int(round(value))
    if rounded < minimum:
        return minimum
    if rounded > maximum:
        return maximum
    return rounded


def _normalise_frame(frame):
    notes = set()
    for note in frame:
        midi_note = _clamp_int(note, 0, 127)
        if midi_note > 0:
            notes.add(midi_note)
    return notes


def _normalise_motor_mode(motor_mode):
    if motor_mode not in {"single", "unison", "round-robin"}:
        raise ValueError("motor_mode deve ser 'single', 'unison' ou 'round-robin'.")
    return motor_mode


def _normalise_channels(channels):
    if channels is None:
        channels = range(1, 7)

    normalised = []
    for channel in channels:
        midi_channel = _clamp_int(channel, 1, 16) - 1
        if midi_channel not in normalised:
            normalised.append(midi_channel)

    if not normalised:
        raise ValueError("channels deve conter pelo menos um canal MIDI.")
    return normalised


def _append_delta(track, delta_ticks):
    track.extend(encode_variable_length_quantity(delta_ticks))


def build_midi_track(
    note_frames,
    frame_ticks,
    tempo_bpm=120.0,
    velocity=96,
    program=0,
    motor_mode="single",
    channels=None,
):
    if frame_ticks <= 0:
        raise ValueError("frame_ticks deve ser positivo.")
    if tempo_bpm <= 0.0:
        raise ValueError("tempo_bpm deve ser positivo.")

    velocity = _clamp_int(velocity, 1, 127)
    program = _clamp_int(program, 0, 127)
    motor_mode = _normalise_motor_mode(motor_mode)
    channels = _normalise_channels(channels)
    microseconds_per_quarter = int(round(60000000.0 / tempo_bpm))

    track = bytearray()
    last_tick = 0

    _append_delta(track, 0)
    track.extend(b"\xFF\x51\x03")
    track.extend(microseconds_per_quarter.to_bytes(3, byteorder="big"))

    for channel in channels:
        _append_delta(track, 0)
        track.extend(bytes([0xC0 | channel, program]))

    active_notes = set()
    active_assignments = {}
    next_round_robin = 0
    for frame_index, frame in enumerate(note_frames):
        current_tick = frame_index * frame_ticks
        desired_note_values = _normalise_frame(frame)
        desired_assignments = {}

        for note in sorted(desired_note_values):
            if motor_mode == "single":
                desired_assignments[note] = (channels[0],)
            elif motor_mode == "unison":
                desired_assignments[note] = tuple(channels)
            elif note in active_assignments:
                desired_assignments[note] = active_assignments[note]
            else:
                desired_assignments[note] = (channels[next_round_robin],)
                next_round_robin = (next_round_robin + 1) % len(channels)

        desired_notes = {
            (channel, note)
            for note, assigned_channels in desired_assignments.items()
            for channel in assigned_channels
        }

        for channel, note in sorted(active_notes - desired_notes):
            _append_delta(track, current_tick - last_tick)
            track.extend(bytes([0x80 | channel, note, 0]))
            last_tick = current_tick

        for channel, note in sorted(desired_notes - active_notes):
            _append_delta(track, current_tick - last_tick)
            track.extend(bytes([0x90 | channel, note, velocity]))
            last_tick = current_tick

        active_notes = desired_notes
        active_assignments = desired_assignments

    final_tick = len(note_frames) * frame_ticks
    for channel, note in sorted(active_notes):
        _append_delta(track, final_tick - last_tick)
        track.extend(bytes([0x80 | channel, note, 0]))
        last_tick = final_tick

    _append_delta(track, 0)
    track.extend(b"\xFF\x2F\x00")
    return bytes(track)


def write_midi_file(
    path,
    note_frames,
    frame_ticks,
    tempo_bpm=120.0,
    velocity=96,
    program=0,
    ppq=480,
    motor_mode="single",
    channels=None,
):
    if ppq <= 0:
        raise ValueError("ppq deve ser positivo.")

    output_dir = os.path.dirname(path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    track = build_midi_track(
        note_frames,
        frame_ticks,
        tempo_bpm=tempo_bpm,
        velocity=velocity,
        program=program,
        motor_mode=motor_mode,
        channels=channels,
    )

    header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, ppq)
    track_chunk = b"MTrk" + struct.pack(">I", len(track)) + track

    with open(path, "wb") as midi_file:
        midi_file.write(header)
        midi_file.write(track_chunk)

    return {
        "path": path,
        "track_size": len(track),
        "frame_ticks": frame_ticks,
        "tempo_bpm": tempo_bpm,
        "ppq": ppq,
        "motor_mode": motor_mode,
    }
