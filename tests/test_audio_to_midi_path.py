import unittest

from examples.audio_to_midi.app import export_audio_to_midi, select_melody_path


class AudioToMidiPathTest(unittest.TestCase):
    def test_path_prefers_continuous_melody_over_stronger_single_frame_jump(self):
        frames = select_melody_path(
            [
                [(60, 0.8), (72, 0.3)],
                [(60, 0.7), (84, 0.9)],
                [(62, 0.8), (84, 0.2)],
            ]
        )

        self.assertEqual(frames, [[60], [60], [62]])

    def test_path_preserves_silence_when_frame_has_no_candidates(self):
        frames = select_melody_path([[(60, 0.8)], [], [(60, 0.8)]])

        self.assertEqual(frames, [[60], [], [60]])

    def test_export_rejects_motor_count_outside_hardware_limit(self):
        with self.assertRaises(ValueError):
            export_audio_to_midi("missing.wav", "missing.mid", motor_count=7)


if __name__ == "__main__":
    unittest.main()
