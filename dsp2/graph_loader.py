import json
import os
import dsp2._dsp2_core as core
from dsp2.signal_io import load_pcm_timeseries_data

# [NOVO] Importamos os nós em Python
from dsp2.nodes_py.debug_node import DebugNode

# [NOVO] Dicionário de registro de nós disponíveis no lado Python
PYTHON_NODES = {
    "DebugNode": DebugNode
}

class GraphLoader:
    @staticmethod
    def load_from_json(engine: core.Engine, filepath: str):
        print(f"[GraphLoader] Lendo montagem de grafo em: {filepath}")
        
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        node_ids = {} # Dicionário (Nome Visual -> ID do C++)
        
        # 1. Instanciar Nós no Engine C++
        for node in data.get('nodes', []):
            name = node['name']
            node_type = node['type']
            
            # [NOVO] Lógica de Instanciação Mista (Python vs C++)
            if node_type in PYTHON_NODES:
                # 1A: O nó foi escrito em Python
                py_node = PYTHON_NODES[node_type]()
                node_id = engine.add_node_obj(py_node)
                print(f" -> Nó alocado PYTHON: {name} ({node_type}) | ID: {node_id}")
            else:
                # 1B: O nó é nativo e otimizado em C++
                node_id = engine.add_node(node_type)
                if node_id == -1:
                    raise ValueError(f"Erro ao instanciar nó '{name}'. O tipo '{node_type}' não existe no core C++.")
                print(f" -> Nó alocado C++: {name} ({node_type}) | ID: {node_id}")
            
            node_ids[name] = node_id
            
            # Leitura Inteligente de Parâmetros (Mantido do original)
            if 'parameters' in node:
                for param_name, value in node['parameters'].items():
                    if node_type == "FileSignalInput" and param_name == "path":
                        wav_path = value
                        if not os.path.isabs(wav_path):
                            wav_path = os.path.join(os.path.dirname(filepath), wav_path)
                        samples, sample_rate = load_pcm_timeseries_data(wav_path)
                        engine.set_node_parameter_array(node_id, "samples", samples)
                        print(f"    - WAV carregado: {wav_path} ({len(samples)} amostras, {sample_rate} Hz)")
                        continue
                        
                    if isinstance(value, list):
                        engine.set_node_parameter_array(node_id, param_name, value)
                        print(f"    - Parâmetro Array configurado: {param_name} = (Tamanho: {len(value)})")
                    else:
                        engine.set_node_parameter(node_id, param_name, float(value))
                        print(f"    - Parâmetro Escalar configurado: {param_name} = {value}")

        # 2. Conectar as Arestas (Mantido do original)
        for edge in data.get('edges', []):
            src = edge['source']
            src_port = edge['source_port']
            dst = edge['dest']
            dst_port = edge['dest_port']
            
            engine.add_edge(node_ids[src], src_port, node_ids[dst], dst_port)
            print(f" -> Cabo ligado: {src}[P:{src_port}] ---> {dst}[P:{dst_port}]")
            
        print("[GraphLoader] Grafo montado com sucesso e injetado no motor de tempo real!\n")
        return node_ids