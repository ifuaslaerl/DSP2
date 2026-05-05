import os
import tempfile
import unittest

from dsp2.midi_io import (
    build_midi_track,
    encode_variable_length_quantity,
    write_midi_file,
)


def extract_note_on_notes(midi_bytes):
    notes = []
    index = 0
    while index < len(midi_bytes):
        status = midi_bytes[index]
        if status == 0x90 and index + 2 < len(midi_bytes):
            note = midi_bytes[index + 1]
            velocity = midi_bytes[index + 2]
            if velocity > 0:
                notes.append(note)
            index += 3
        else:
            index += 1
    return notes


def extract_note_on_channels(midi_bytes):
    channels = []
    index = 0
    while index < len(midi_bytes):
        status = midi_bytes[index]
        if 0x90 <= status <= 0x9F and index + 2 < len(midi_bytes):
            velocity = midi_bytes[index + 2]
            if velocity > 0:
                channels.append((status & 0x0F) + 1)
            index += 3
        else:
            index += 1
    return channels


class MidiIoTest(unittest.TestCase):
    def test_variable_length_quantity_encoding(self):
        self.assertEqual(encode_variable_length_quantity(0), b"\x00")
        self.assertEqual(encode_variable_length_quantity(127), b"\x7f")
        self.assertEqual(encode_variable_length_quantity(128), b"\x81\x00")
        self.assertEqual(encode_variable_length_quantity(8192), b"\xc0\x00")

    def test_write_midi_file_header_and_track(self):
        handle = tempfile.NamedTemporaryFile(suffix=".mid", delete=False)
        midi_path = handle.name
        handle.close()

        try:
            write_midi_file(midi_path, [[60]], frame_ticks=240, tempo_bpm=120.0)
            with open(midi_path, "rb") as midi_file:
                payload = midi_file.read()

            self.assertEqual(payload[0:4], b"MThd")
            self.assertEqual(payload[8:14], b"\x00\x00\x00\x01\x01\xe0")
            self.assertEqual(payload[14:18], b"MTrk")
            self.assertIn(bytes([0x90, 60, 96]), payload)
            self.assertIn(bytes([0x80, 60, 0]), payload)
            self.assertTrue(payload.endswith(b"\x00\xff\x2f\x00"))
        finally:
            os.unlink(midi_path)

    def test_repeated_notes_are_sustained(self):
        track = build_midi_track([[60], [60], [60]], frame_ticks=120)

        self.assertEqual(track.count(bytes([0x90, 60, 96])), 1)
        self.assertEqual(track.count(bytes([0x80, 60, 0])), 1)

    def test_chord_frames_emit_multiple_note_on_events(self):
        track = build_midi_track([[39, 55]], frame_ticks=120)
        notes = extract_note_on_notes(track)

        self.assertEqual(notes, [39, 55])

    def test_single_motor_mode_writes_channel_one(self):
        track = build_midi_track([[60]], frame_ticks=120, motor_mode="single")

        self.assertEqual(extract_note_on_channels(track), [1])

    def test_unison_motor_mode_writes_channels_one_to_six(self):
        track = build_midi_track([[60]], frame_ticks=120, motor_mode="unison")

        self.assertEqual(extract_note_on_channels(track), [1, 2, 3, 4, 5, 6])

    def test_round_robin_motor_mode_alternates_channels_between_notes(self):
        track = build_midi_track(
            [[60], [], [62], [], [64]],
            frame_ticks=120,
            motor_mode="round-robin",
        )

        self.assertEqual(extract_note_on_channels(track), [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
