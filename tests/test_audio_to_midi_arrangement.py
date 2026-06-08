import unittest

from examples.audio_to_midi.app import extract_bass, extract_melody, get_profile_parameters
from examples.audio_to_midi.arrangement import (
    NoteEvent,
    PitchCandidate,
    arrange_for_motors,
    duration_ms_to_frames,
)


def active_channels(frames):
    channels = set()
    for frame in frames:
        for index, note in enumerate(frame):
            if note > 0:
                channels.add(index + 1)
    return channels


def assert_no_voice_overlaps(testcase, voices):
    for voice in voices:
        previous_end = -1
        for event in voice.events:
            testcase.assertGreaterEqual(event.start_frame, previous_end)
            testcase.assertLess(event.start_frame, event.end_frame)
            previous_end = event.end_frame


class AudioToMidiArrangementTest(unittest.TestCase):
    def test_duration_ms_conversion_uses_hop_duration(self):
        self.assertEqual(duration_ms_to_frames(100.0, hop_size=10, sample_rate=1000), 10)
        self.assertEqual(duration_ms_to_frames(70.0, hop_size=10, sample_rate=1000), 7)
        self.assertEqual(duration_ms_to_frames(1.0, hop_size=10, sample_rate=1000), 1)

    def test_melody_only_uses_channel_one_only(self):
        _, frames = arrange_for_motors(
            [NoteEvent(60, 0, 4, 0.9)],
            mode="melody_only",
            frame_count=4,
            motor_count=6,
        )

        self.assertEqual(active_channels(frames), {1})
        self.assertEqual(frames[0], [60, 0, 0, 0, 0, 0])

    def test_melody_bass_uses_at_most_first_two_channels(self):
        _, frames = arrange_for_motors(
            [NoteEvent(64, 0, 4, 0.9)],
            bass_events=[NoteEvent(40, 1, 4, 0.8)],
            mode="melody_bass",
            frame_count=4,
            motor_count=6,
        )

        self.assertLessEqual(active_channels(frames), {1, 2})
        self.assertEqual(frames[1], [64, 40, 0, 0, 0, 0])

    def test_recognizable_orchestra_v2_limits_channels_and_voice_overlap(self):
        voices, frames = arrange_for_motors(
            [NoteEvent(64, 0, 8, 0.95), NoteEvent(67, 8, 14, 0.9)],
            bass_events=[NoteEvent(40, 0, 14, 0.8)],
            mode="recognizable_orchestra_v2",
            frame_count=14,
            motor_count=6,
            stable_note_frames=4,
        )

        self.assertLessEqual(max(active_channels(frames)), 6)
        self.assertLessEqual(len(frames[0]), 6)
        assert_no_voice_overlaps(self, voices)

    def test_melody_extraction_respects_midi_range(self):
        candidate_frames = [
            [PitchCandidate(0, 52, 0.9), PitchCandidate(0, 60, 0.7)],
            [PitchCandidate(1, 52, 0.9), PitchCandidate(1, 60, 0.7)],
        ]

        events, frames = extract_melody(
            candidate_frames,
            min_note_frames=1,
            merge_gap_frames=0,
            min_midi_note=55,
            max_midi_note=83,
        )

        self.assertEqual([event.pitch for event in events], [60])
        self.assertEqual(frames, [[60], [60]])

    def test_bass_extraction_respects_midi_range(self):
        candidate_frames = [
            [PitchCandidate(0, 40, 0.7), PitchCandidate(0, 60, 0.95)],
            [PitchCandidate(1, 40, 0.7), PitchCandidate(1, 60, 0.95)],
        ]

        events, frames = extract_bass(
            candidate_frames,
            min_note_frames=1,
            merge_gap_frames=0,
            min_midi_note=32,
            max_midi_note=55,
        )

        self.assertEqual([event.pitch for event in events], [40])
        self.assertEqual(frames, [[40], [40]])

    def test_conservative_harmony_can_leave_extra_channels_silent(self):
        _, frames = arrange_for_motors(
            [NoteEvent(64, 0, 8, 0.2)],
            mode="recognizable_orchestra_v2",
            frame_count=8,
            motor_count=6,
            harmony_confidence=0.55,
            stable_note_frames=4,
        )

        self.assertEqual(active_channels(frames), {1})
        for frame in frames:
            self.assertEqual(frame[2:], [0, 0, 0, 0])

    def test_recognizable_orchestra_v2_profile_parameters(self):
        profile = get_profile_parameters("recognizable-orchestra-v2")

        self.assertEqual(profile["mode"], "recognizable_orchestra_v2")
        self.assertEqual(profile["motor_mode"], "voices")
        self.assertEqual(profile["motor_count"], 6)
        self.assertEqual(profile["min_midi_note"], 55)
        self.assertEqual(profile["max_midi_note"], 83)
        self.assertAlmostEqual(profile["min_note_ms"], 100.0)
        self.assertAlmostEqual(profile["merge_gap_ms"], 70.0)


if __name__ == "__main__":
    unittest.main()
