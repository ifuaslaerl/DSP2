import json
import os
import dsp2._dsp2_core as core
from dsp2.audio_io import load_wav_mono

class GraphLoader:
    @staticmethod
    def load_from_json(engine: core.Engine, filepath: str):
        print(f"[GraphLoader] Lendo montagem de grafo em: {filepath}")
        
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        node_ids = {} # Dicionario (Nome Visual -> ID do C++)
        
        # 1. Instanciar Nos no Engine C++
        for node in data.get('nodes', []):
            name = node['name']
            node_type = node['type']
            
            node_id = engine.add_node(node_type)
            if node_id == -1:
                raise ValueError(f"Erro ao instanciar no '{name}'. O tipo '{node_type}' nao existe no core C++.")
                
            node_ids[name] = node_id
            print(f" -> No alocado C++: {name} ({node_type}) | ID: {node_id}")
            
            # [NOVO] Leitura Inteligente de Parametros (Escalares vs Arrays)
            if 'parameters' in node:
                for param_name, value in node['parameters'].items():
                    if node_type == "AudioFileInput" and param_name == "path":
                        wav_path = value
                        if not os.path.isabs(wav_path):
                            wav_path = os.path.join(os.path.dirname(filepath), wav_path)
                        samples, sample_rate = load_wav_mono(wav_path)
                        engine.set_node_parameter_array(node_id, "samples", samples)
                        print(
                            f"    - WAV carregado: {wav_path} "
                            f"({len(samples)} amostras, {sample_rate} Hz)"
                        )
                        continue
                    if isinstance(value, list):
                        # Se for uma lista no JSON, envia como Array para o C++
                        engine.set_node_parameter_array(node_id, param_name, value)
                        print(f"    - Parametro Array configurado: {param_name} = (Tamanho: {len(value)})")
                    else:
                        # Se for um numero unico, envia o double normal
                        engine.set_node_parameter(node_id, param_name, float(value))
                        print(f"    - Parametro Escalar configurado: {param_name} = {value}")

        # 2. Conectar as Arestas (Zero-Copy routing + Multirate SDF)
        for edge in data.get('edges', []):
            src = edge['source']
            src_port = edge['source_port']
            dst = edge['dest']
            dst_port = edge['dest_port']
            
            engine.add_edge(node_ids[src], src_port, node_ids[dst], dst_port)
            print(f" -> Cabo ligado: {src}[P:{src_port}] ---> {dst}[P:{dst_port}]")
            
        print("[GraphLoader] Grafo montado com sucesso e injetado no motor de tempo real!\n")
        return node_ids
