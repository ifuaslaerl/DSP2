import json
import os
import struct
import tempfile
import unittest
import wave

from dev_panel.signal_tester import (
    DSP2TestHarness,
    calculate_signal_metrics,
    export_wav_files,
    normalize_samples_for_wav,
    resolve_wav_output_paths,
    write_float32_wav,
    write_pcm16_wav,
)


class SignalReportTest(unittest.TestCase):
    def write_graph(self, data):
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", encoding="utf-8", delete=False
        )
        try:
            json.dump(data, handle)
            return handle.name
        finally:
            handle.close()

    def test_constant_metrics(self):
        metrics = calculate_signal_metrics([6.0, 6.0, 6.0])

        self.assertEqual(metrics["min"], 6.0)
        self.assertEqual(metrics["max"], 6.0)
        self.assertEqual(metrics["rms"], 6.0)
        self.assertEqual(metrics["peak"], 6.0)
        self.assertEqual(metrics["dc_offset"], 6.0)

    def test_balanced_signal_metrics(self):
        metrics = calculate_signal_metrics([-1.0, 1.0])

        self.assertEqual(metrics["min"], -1.0)
        self.assertEqual(metrics["max"], 1.0)
        self.assertEqual(metrics["rms"], 1.0)
        self.assertEqual(metrics["peak"], 1.0)
        self.assertEqual(metrics["dc_offset"], 0.0)

    def test_empty_metrics(self):
        metrics = calculate_signal_metrics([])

        self.assertIsNone(metrics["min"])
        self.assertIsNone(metrics["max"])
        self.assertIsNone(metrics["rms"])
        self.assertIsNone(metrics["peak"])
        self.assertIsNone(metrics["dc_offset"])

    def test_wav_normalization_scales_by_peak(self):
        normalized = normalize_samples_for_wav([-2.0, 0.0, 2.0])

        self.assertAlmostEqual(float(normalized[0]), -1.0)
        self.assertAlmostEqual(float(normalized[1]), 0.0)
        self.assertAlmostEqual(float(normalized[2]), 1.0)

    def test_wav_normalization_preserves_silence(self):
        normalized = normalize_samples_for_wav([0.0, 0.0])

        self.assertEqual(list(normalized), [0.0, 0.0])

    def test_resolve_wav_output_paths(self):
        self.assertEqual(
            resolve_wav_output_paths("dev_panel/out", "pcm16"),
            {"pcm16": "dev_panel/out_pcm16.wav"},
        )
        self.assertEqual(
            resolve_wav_output_paths("dev_panel/out", "float32"),
            {"float32": "dev_panel/out_float32.wav"},
        )
        self.assertEqual(
            resolve_wav_output_paths("dev_panel/out", "both"),
            {
                "pcm16": "dev_panel/out_pcm16.wav",
                "float32": "dev_panel/out_float32.wav",
            },
        )

    def test_write_pcm16_wav(self):
        handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        wav_path = handle.name
        handle.close()

        try:
            write_pcm16_wav(wav_path, [-1.0, 0.0, 1.0], 22050.0)
            with wave.open(wav_path, "rb") as wav:
                self.assertEqual(wav.getnchannels(), 1)
                self.assertEqual(wav.getsampwidth(), 2)
                self.assertEqual(wav.getframerate(), 22050)
                self.assertEqual(wav.getnframes(), 3)
        finally:
            os.unlink(wav_path)

    def test_write_float32_wav(self):
        handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        wav_path = handle.name
        handle.close()

        try:
            write_float32_wav(wav_path, [-1.0, 0.0, 1.0], 44100.0)
            with open(wav_path, "rb") as wav:
                content = wav.read()

            self.assertEqual(content[0:4], b"RIFF")
            self.assertEqual(content[8:12], b"WAVE")
            self.assertEqual(content[20:22], struct.pack("<H", 3))
            self.assertEqual(content[22:24], struct.pack("<H", 1))
            self.assertEqual(content[24:28], struct.pack("<I", 44100))
            self.assertEqual(content[34:36], struct.pack("<H", 32))
            self.assertEqual(content[36:40], b"data")
            self.assertEqual(struct.unpack("<I", content[40:44])[0], 12)
        finally:
            os.unlink(wav_path)

    def test_markdown_report_from_constant_gain_graph(self):
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
        report_handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", encoding="utf-8", delete=False
        )
        report_path = report_handle.name
        report_handle.close()

        try:
            tester = DSP2TestHarness(sample_rate=44100.0, block_size=8)
            tester.load_graph(graph_path)
            data, logs = tester.run_and_capture(num_blocks=1)
            wav_prefix = tempfile.NamedTemporaryFile(delete=True).name
            wav_export = export_wav_files(data, "Amp", 0, wav_prefix, "pcm16")

            tester.write_report(
                report_path,
                data,
                logs,
                graph_path,
                "dev_panel/test_signal.png",
                num_blocks=1,
                wav_export=wav_export,
            )

            with open(report_path, "r", encoding="utf-8") as f:
                report = f.read()

            self.assertIn("# D(SP)^2 - Relatorio de Simulacao do Grafo", report)
            self.assertIn("| Source | Constant | 0 |", report)
            self.assertIn("| Amp | Gain | 1 |", report)
            self.assertIn("| Source | 0 | Amp | 0 |", report)
            self.assertIn("| Amp | 0 | 8 | 44100", report)
            self.assertIn("6", report)
            self.assertIn("Nenhum evento foi coletado", report)
            self.assertIn("dev_panel/test_signal.png", report)
            self.assertIn("## Export WAV", report)
            self.assertIn("Amp", report)
            self.assertTrue(os.path.exists(wav_export["files"]["pcm16"]))
        finally:
            os.unlink(graph_path)
            os.unlink(report_path)
            if "wav_export" in locals():
                for path in wav_export["files"].values():
                    if os.path.exists(path):
                        os.unlink(path)


if __name__ == "__main__":
    unittest.main()
