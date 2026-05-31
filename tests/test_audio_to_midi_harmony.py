import unittest

from examples.audio_to_midi.app import harmonize_note_frames


class AudioToMidiHarmonyTest(unittest.TestCase):
    def test_d_minor_melody_note_generates_six_voices(self):
        frames = harmonize_note_frames(
            [[62]],
            harmony_key="D",
            harmony_scale="minor",
            harmony_voices=6,
            min_midi_note=36,
            max_midi_note=84,
        )

        self.assertEqual(len(frames[0]), 6)
        self.assertEqual(frames[0][0], 62)
        self.assertEqual(len(frames[0]), len(set(frames[0])))
        for note in frames[0]:
            self.assertGreaterEqual(note, 36)
            self.assertLessEqual(note, 84)

    def test_empty_frame_generates_silence(self):
        frames = harmonize_note_frames([[]], harmony_voices=6)

        self.assertEqual(frames, [[]])

    def test_out_of_scale_melody_is_preserved_on_first_voice(self):
        frames = harmonize_note_frames(
            [[61]],
            harmony_key="D",
            harmony_scale="minor",
            harmony_voices=4,
            min_midi_note=36,
            max_midi_note=84,
        )

        self.assertEqual(frames[0][0], 61)
        self.assertEqual(len(frames[0]), 4)

    def test_harmony_respects_configured_note_range(self):
        frames = harmonize_note_frames(
            [[74]],
            harmony_key="D",
            harmony_scale="minor",
            harmony_voices=6,
            min_midi_note=70,
            max_midi_note=76,
        )

        for note in frames[0]:
            self.assertGreaterEqual(note, 70)
            self.assertLessEqual(note, 76)


if __name__ == "__main__":
    unittest.main()
