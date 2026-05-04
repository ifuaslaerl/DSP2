import json
import os
import tempfile
import unittest

from dev_panel.compare_simulations import (
    build_comparison_report,
    calculate_delta,
    compare_captures,
    run_simulation,
    write_comparison_report,
)


class CompareSimulationsTest(unittest.TestCase):
    def write_graph(self, data):
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", encoding="utf-8", delete=False
        )
        try:
            json.dump(data, handle)
            return handle.name
        finally:
            handle.close()

    def test_delta_with_nonzero_baseline(self):
        delta = calculate_delta(2.0, 3.0)

        self.assertEqual(delta["absolute"], 1.0)
        self.assertEqual(delta["percent"], 50.0)

    def test_delta_percent_is_none_with_zero_baseline(self):
        delta = calculate_delta(0.0, 3.0)

        self.assertEqual(delta["absolute"], 3.0)
        self.assertIsNone(delta["percent"])

    def test_missing_signal_detection(self):
        baseline = {
            "A": {
                0: {
                    "samples": [1.0],
                    "sample_rate": 44100.0,
                }
            }
        }
        candidate = {
            "B": {
                0: {
                    "samples": [1.0],
                    "sample_rate": 44100.0,
                }
            }
        }

        statuses = {
            (item["node"], item["status"]) for item in compare_captures(baseline, candidate)
        }

        self.assertIn(("A", "missing_candidate"), statuses)
        self.assertIn(("B", "missing_baseline"), statuses)

    def test_markdown_comparison_from_constant_gain_graphs(self):
        baseline_path = self.write_graph(
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
        candidate_path = self.write_graph(
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
                        "parameters": {"gain": 4.0},
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
            baseline_data, baseline_logs = run_simulation(
                baseline_path, sample_rate=44100.0, block_size=8, num_blocks=1
            )
            candidate_data, candidate_logs = run_simulation(
                candidate_path, sample_rate=44100.0, block_size=8, num_blocks=1
            )
            comparisons = compare_captures(baseline_data, candidate_data)
            report = build_comparison_report(
                comparisons,
                baseline_logs,
                candidate_logs,
                baseline_path,
                candidate_path,
                sample_rate=44100.0,
                block_size=8,
                num_blocks=1,
            )
            write_comparison_report(report_path, report)

            with open(report_path, "r", encoding="utf-8") as f:
                report_text = f.read()

            self.assertIn("# D(SP)^2 - Comparador de Simulacoes do Grafo", report_text)
            self.assertIn("| Amp | 0 | ok | 8 | 8 | 44100 | 44100 | 6 | 8 | 2 | 33.3333", report_text)
            self.assertIn("Todos os sinais foram pareados", report_text)
            self.assertIn("Nenhum evento foi coletado", report_text)
        finally:
            os.unlink(baseline_path)
            os.unlink(candidate_path)
            os.unlink(report_path)


if __name__ == "__main__":
    unittest.main()
