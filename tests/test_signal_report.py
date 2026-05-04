import json
import os
import tempfile
import unittest

from dev_panel.signal_tester import DSP2TestHarness, calculate_signal_metrics


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
            tester.write_report(
                report_path,
                data,
                logs,
                graph_path,
                "dev_panel/test_signal.png",
                num_blocks=1,
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
        finally:
            os.unlink(graph_path)
            os.unlink(report_path)


if __name__ == "__main__":
    unittest.main()
