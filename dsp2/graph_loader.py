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
            
            # [NOVO] Leitura Inteligente de Parâmetros (Escalares vs Arrays)
            if 'parameters' in node:
                for param_name, value in node['parameters'].items():
                    if isinstance(value, list):
                        # Se for uma lista no JSON, envia como Array para o C++
                        engine.set_node_parameter_array(node_id, param_name, value)
                        print(f"    - Parâmetro Array configurado: {param_name} = (Tamanho: {len(value)})")
                    else:
                        # Se for um número único, envia o double normal
                        engine.set_node_parameter(node_id, param_name, float(value))
                        print(f"    - Parâmetro Escalar configurado: {param_name} = {value}")

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