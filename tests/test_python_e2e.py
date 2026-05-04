import json
import math
import os
import struct
import tempfile
import unittest
import wave

import dsp2._dsp2_core as core
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


if __name__ == "__main__":
    unittest.main()
