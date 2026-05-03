import json
import os
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
