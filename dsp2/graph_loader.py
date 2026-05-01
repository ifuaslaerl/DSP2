import json
import dsp2._dsp2_core as core

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
            
            node_id = engine.add_node(node_type)
            if node_id == -1:
                raise ValueError(f"Erro ao instanciar nó '{name}'. O tipo '{node_type}' não existe no core C++.")
                
            node_ids[name] = node_id
            print(f" -> Nó alocado C++: {name} ({node_type}) | ID: {node_id}")

        # 2. Conectar as Arestas (Zero-Copy routing)
        for edge in data.get('edges', []):
            src = edge['source']
            src_port = edge['source_port']
            dst = edge['dest']
            dst_port = edge['dest_port']
            
            engine.add_edge(node_ids[src], src_port, node_ids[dst], dst_port)
            print(f" -> Cabo ligado: {src}[P:{src_port}] ---> {dst}[P:{dst_port}]")
            
        print("[GraphLoader] Grafo montado com sucesso e injetado no motor de tempo real!\n")
        return node_ids