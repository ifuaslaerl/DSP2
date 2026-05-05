import json
import math
import os
import struct
import tempfile
import unittest
import wave

import dsp2._dsp2_core as core
from dsp2.audio_to_midi import collect_midi_note_frames, export_audio_to_midi
from dsp2.graph_loader import GraphLoader


class PythonJsonE2ETest(unittest.TestCase):
    def write_graph(self, data):
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", encoding="utf-8", delete=False
        )
        try:
            json.dump(data, handle)
            return handle.name
        finally:
            handle.close()

    def test_constant_gain_graph_from_json(self):
        graph_path = self.write_graph(
            {
                "nodes": [
                    {
                        "name": "Source",
                        "type": "Constant",
                        "parameters": {"value": 2.0},
                    },
                    {
                        "name": "Amp",
                        "type": "Gain",
                        "parameters": {"gain": 3.0},
                    },
                ],
                "edges": [
                    {
                        "source": "Source",
                        "source_port": 0,
                        "dest": "Amp",
                        "dest_port": 0,
                    }
                ],
            }
        )

        try:
            engine = core.Engine()
            engine.set_signal_parameters(44100.0, 8)
            node_ids = GraphLoader.load_from_json(engine, graph_path)
            engine.prepare_engine()
            engine.process_block()

            output = engine.get_node_output(node_ids["Amp"], 0)
            self.assertEqual(len(output), 8)
            for sample in output:
                self.assertAlmostEqual(sample, 6.0, places=9)
        finally:
            os.unlink(graph_path)

    def test_unknown_node_type_raises_value_error(self):
        graph_path = self.write_graph(
            {
                "nodes": [
                    {
                        "name": "Missing",
                        "type": "NoSuchNode",
                    }
                ],
                "edges": [],
            }
        )

        try:
            engine = core.Engine()
            with self.assertRaises(ValueError):
                GraphLoader.load_from_json(engine, graph_path)
        finally:
            os.unlink(graph_path)

    def test_audio_file_input_graph_from_wav_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wav_path = os.path.join(tmpdir, "input.wav")
            graph_path = os.path.join(tmpdir, "graph.json")

            with wave.open(wav_path, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(8000)
                wav.writeframes(struct.pack("<hhh", 0, 8192, -8192))

            with open(graph_path, "w", encoding="utf-8") as graph_file:
                json.dump(
                    {
                        "nodes": [
                            {
                                "name": "Audio",
                                "type": "AudioFileInput",
                                "parameters": {"path": "input.wav"},
                            },
                            {
                                "name": "Amp",
                                "type": "Gain",
                                "parameters": {"gain": 2.0},
                            },
                        ],
                        "edges": [
                            {
                                "source": "Audio",
                                "source_port": 0,
                                "dest": "Amp",
                                "dest_port": 0,
                            }
                        ],
                    },
                    graph_file,
                )

            engine = core.Engine()
            engine.set_signal_parameters(8000.0, 4)
            node_ids = GraphLoader.load_from_json(engine, graph_path)
            engine.prepare_engine()
            engine.process_block()

            output = engine.get_node_output(node_ids["Amp"], 0)
            self.assertEqual(len(output), 4)
            self.assertAlmostEqual(output[0], 0.0, places=9)
            self.assertAlmostEqual(output[1], 0.5, places=9)
            self.assertAlmostEqual(output[2], -0.5, places=9)
            self.assertAlmostEqual(output[3], 0.0, places=9)

    def test_spectrum_analyser_graph_from_wav_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wav_path = os.path.join(tmpdir, "sine.wav")
            graph_path = os.path.join(tmpdir, "graph.json")

            pcm_samples = []
            for i in range(16):
                value = math.sin(2.0 * math.pi * 3.0 * i / 16.0)
                pcm_samples.append(int(round(value * 30000.0)))

            with wave.open(wav_path, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16)
                wav.writeframes(struct.pack("<" + "h" * len(pcm_samples), *pcm_samples))

            with open(graph_path, "w", encoding="utf-8") as graph_file:
                json.dump(
                    {
                        "nodes": [
                            {
                                "name": "Audio",
                                "type": "AudioFileInput",
                                "parameters": {"path": "sine.wav"},
                            },
                            {
                                "name": "Spectrum",
                                "type": "SpectrumAnalyzer",
                                "parameters": {"fft_size": 16},
                            },
                        ],
                        "edges": [
                            {
                                "source": "Audio",
                                "source_port": 0,
                                "dest": "Spectrum",
                                "dest_port": 0,
                            }
                        ],
                    },
                    graph_file,
                )

            engine = core.Engine()
            engine.set_signal_parameters(16.0, 16)
            node_ids = GraphLoader.load_from_json(engine, graph_path)
            engine.prepare_engine()
            engine.process_block()

            self.assertEqual(engine.get_node_output_port_count(node_ids["Spectrum"]), 2)
            power = engine.get_node_output(node_ids["Spectrum"], 0)
            frequencies = engine.get_node_output(node_ids["Spectrum"], 1)
            self.assertEqual(len(power), 9)
            self.assertEqual(len(frequencies), 9)
            self.assertAlmostEqual(frequencies[3], 3.0, places=9)
            self.assertEqual(max(range(len(power)), key=lambda index: power[index]), 3)

    def test_spectral_peak_picker_graph_from_wav_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wav_path = os.path.join(tmpdir, "two_sines.wav")
            graph_path = os.path.join(tmpdir, "graph.json")

            sample_rate = 1024
            block_size = 256
            first_freq = 80.0
            second_freq = 200.0
            pcm_samples = []
            for i in range(block_size):
                value = (
                    math.sin(2.0 * math.pi * first_freq * i / sample_rate)
                    + 0.7 * math.sin(2.0 * math.pi * second_freq * i / sample_rate)
                )
                pcm_samples.append(int(round((value / 1.7) * 30000.0)))

            with wave.open(wav_path, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                wav.writeframes(struct.pack("<" + "h" * len(pcm_samples), *pcm_samples))

            with open(graph_path, "w", encoding="utf-8") as graph_file:
                json.dump(
                    {
                        "nodes": [
                            {
                                "name": "Audio",
                                "type": "AudioFileInput",
                                "parameters": {"path": "two_sines.wav"},
                            },
                            {
                                "name": "Window",
                                "type": "Windowing",
                                "parameters": {"type": 0},
                            },
                            {
                                "name": "Spectrum",
                                "type": "SpectrumAnalyzer",
                                "parameters": {"fft_size": block_size},
                            },
                            {
                                "name": "Peaks",
                                "type": "SpectralPeakPicker",
                                "parameters": {
                                    "peak_count": 2,
                                    "min_frequency": 20.0,
                                    "threshold": 0.001,
                                    "min_bin_distance": 2,
                                },
                            },
                            {
                                "name": "Midi",
                                "type": "FrequencyToMidiNote",
                            },
                        ],
                        "edges": [
                            {
                                "source": "Audio",
                                "source_port": 0,
                                "dest": "Window",
                                "dest_port": 0,
                            },
                            {
                                "source": "Window",
                                "source_port": 0,
                                "dest": "Spectrum",
                                "dest_port": 0,
                            },
                            {
                                "source": "Spectrum",
                                "source_port": 0,
                                "dest": "Peaks",
                                "dest_port": 0,
                            },
                            {
                                "source": "Spectrum",
                                "source_port": 1,
                                "dest": "Peaks",
                                "dest_port": 1,
                            },
                            {
                                "source": "Peaks",
                                "source_port": 0,
                                "dest": "Midi",
                                "dest_port": 0,
                            },
                        ],
                    },
                    graph_file,
                )

            engine = core.Engine()
            engine.set_signal_parameters(float(sample_rate), block_size)
            node_ids = GraphLoader.load_from_json(engine, graph_path)
            engine.prepare_engine()
            engine.process_block()

            peak_frequencies = engine.get_node_output(node_ids["Peaks"], 0)
            peak_powers = engine.get_node_output(node_ids["Peaks"], 1)
            midi_notes = engine.get_node_output(node_ids["Midi"], 0)
            self.assertEqual(len(peak_frequencies), 2)
            self.assertEqual(len(peak_powers), 2)
            self.assertEqual(len(midi_notes), 2)
            self.assertIn(80.0, peak_frequencies)
            self.assertIn(200.0, peak_frequencies)
            self.assertIn(39.0, midi_notes)
            self.assertIn(55.0, midi_notes)
            self.assertGreater(peak_powers[0], 0.0)
            self.assertGreater(peak_powers[1], 0.0)

    def test_audio_to_midi_export_from_wav_path_uses_public_api(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wav_path = os.path.join(tmpdir, "two_sines.wav")
            midi_path = os.path.join(tmpdir, "two_sines.mid")

            sample_rate = 1024
            block_size = 256
            first_freq = 80.0
            second_freq = 200.0
            pcm_samples = []
            for i in range(block_size):
                value = (
                    math.sin(2.0 * math.pi * first_freq * i / sample_rate)
                    + 0.7 * math.sin(2.0 * math.pi * second_freq * i / sample_rate)
                )
                pcm_samples.append(int(round((value / 1.7) * 30000.0)))

            with wave.open(wav_path, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                wav.writeframes(struct.pack("<" + "h" * len(pcm_samples), *pcm_samples))

            result = export_audio_to_midi(
                wav_path,
                midi_path,
                block_size=block_size,
                fft_size=block_size,
                threshold=0.001,
                min_bin_distance=2,
            )

            self.assertTrue(os.path.exists(midi_path))
            self.assertEqual(result["block_count"], 1)
            self.assertIn(39, result["frames"][0])
            self.assertIn(55, result["frames"][0])
            self.assertLessEqual(len(result["frames"][0]), 6)

            with open(midi_path, "rb") as midi_file:
                payload = midi_file.read()

            self.assertEqual(payload[0:4], b"MThd")
            self.assertIn(bytes([0x90, 39, 96]), payload)
            self.assertIn(bytes([0x90, 55, 96]), payload)

    def test_audio_to_midi_collects_empty_frames_for_silence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wav_path = os.path.join(tmpdir, "silence.wav")

            sample_rate = 1024
            block_size = 256
            pcm_samples = [0] * (block_size * 2)

            with wave.open(wav_path, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                wav.writeframes(struct.pack("<" + "h" * len(pcm_samples), *pcm_samples))

            result = collect_midi_note_frames(
                wav_path,
                block_size=block_size,
                fft_size=block_size,
                peak_count=6,
                threshold=0.001,
            )

            self.assertEqual(result["block_count"], 2)
            self.assertEqual(result["frames"], [[], []])

    def test_audio_to_midi_silence_writes_rest_only_midi(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wav_path = os.path.join(tmpdir, "silence.wav")
            midi_path = os.path.join(tmpdir, "silence.mid")

            sample_rate = 1024
            block_size = 256
            pcm_samples = [0] * block_size

            with wave.open(wav_path, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                wav.writeframes(struct.pack("<" + "h" * len(pcm_samples), *pcm_samples))

            result = export_audio_to_midi(
                wav_path,
                midi_path,
                block_size=block_size,
                fft_size=block_size,
                peak_count=6,
                threshold=0.001,
            )

            self.assertEqual(result["frames"], [[]])
            with open(midi_path, "rb") as midi_file:
                payload = midi_file.read()

            note_on_count = 0
            for index in range(len(payload) - 2):
                if payload[index] == 0x90 and payload[index + 2] > 0:
                    note_on_count += 1

            self.assertEqual(note_on_count, 0)
            self.assertTrue(payload.endswith(b"\x00\xff\x2f\x00"))


if __name__ == "__main__":
    unittest.main()
