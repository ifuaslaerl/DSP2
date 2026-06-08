import unittest
from unittest import mock

from examples.audio_to_midi.app import (
    apply_profile_to_args,
    export_audio_to_midi,
    get_profile_parameters,
    resolve_analysis_audio_path,
    select_melody_path,
)


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

    def test_recognizable_orchestra_profile_parameters(self):
        profile = get_profile_parameters("recognizable-orchestra")

        self.assertEqual(profile["mode"], "harmony")
        self.assertEqual(profile["motor_mode"], "voices")
        self.assertEqual(profile["motor_count"], 6)
        self.assertEqual(profile["block_size"], 2048)
        self.assertEqual(profile["fft_size"], 4096)
        self.assertEqual(profile["hop_size"], 1024)
        self.assertEqual(profile["min_midi_note"], 32)
        self.assertEqual(profile["max_midi_note"], 83)
        self.assertAlmostEqual(profile["relative_threshold"], 0.08)
        self.assertAlmostEqual(profile["min_confidence"], 0.20)
        self.assertEqual(profile["min_note_frames"], 8)
        self.assertEqual(profile["merge_gap_frames"], 3)
        self.assertAlmostEqual(profile["jump_penalty"], 0.10)
        self.assertAlmostEqual(profile["octave_jump_penalty"], 0.70)

    def test_profile_application_preserves_explicit_cli_overrides(self):
        class Args:
            profile = "recognizable-orchestra"
            mode = "melody"
            motor_mode = None
            motor_count = 1
            block_size = 1024
            fft_size = None
            hop_size = None
            min_midi_note = 36
            max_midi_note = 84
            relative_threshold = 0.05
            min_confidence = 0.2
            min_note_frames = 2
            merge_gap_frames = 1
            path_candidate_count = 5
            harmony_voices = 6
            jump_penalty = 0.04
            octave_jump_penalty = 0.25
            silence_transition_penalty = 0.10

        args = Args()
        apply_profile_to_args(args, {"min_confidence", "jump_penalty"})

        self.assertEqual(args.mode, "harmony")
        self.assertEqual(args.motor_mode, "voices")
        self.assertEqual(args.motor_count, 6)
        self.assertEqual(args.min_midi_note, 32)
        self.assertEqual(args.max_midi_note, 83)
        self.assertAlmostEqual(args.min_confidence, 0.2)
        self.assertAlmostEqual(args.jump_penalty, 0.04)
        self.assertAlmostEqual(args.octave_jump_penalty, 0.70)

    def test_wav_input_is_used_directly_for_analysis(self):
        path, converted = resolve_analysis_audio_path("musica.wav", "/tmp")

        self.assertEqual(path, "musica.wav")
        self.assertFalse(converted)

    def test_non_wav_input_is_converted_for_analysis(self):
        with mock.patch("examples.audio_to_midi.app.convert_to_analysis_wav") as convert:
            path, converted = resolve_analysis_audio_path("musica.mp3", "/tmp/dsp2-test")

        self.assertEqual(path, "/tmp/dsp2-test/analysis_input.wav")
        self.assertTrue(converted)
        convert.assert_called_once_with("musica.mp3", "/tmp/dsp2-test/analysis_input.wav")


if __name__ == "__main__":
    unittest.main()
