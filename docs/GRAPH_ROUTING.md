# Guia de Roteamento de Grafo (JSON)

O $D(SP)^2$ permite a construção visual e orientada a dados de pipelines. A topologia do grafo é definida em um arquivo JSON e lida pelo `GraphLoader` em Python.

## Estrutura do JSON

O arquivo deve conter duas listas principais: `nodes` (os módulos de processamento) e `edges` (os cabos que ligam os módulos).

### 1. Nodes (Nós)
- `name`: O apelido (ID visual) do nó na sua simulação. Deve ser único.
- `type`: O tipo de módulo C++ real que será instanciado (deve estar registrado na `NodeFactory`).

### 2. Edges (Arestas/Cabos)
O motor C++ utiliza roteamento **Zero-Copy**. Isso significa que conectar um cabo faz com que a memória de entrada do destino aponte para o endereço físico da saída da origem.
- `source`: O `name` do nó de origem.
- `source_port`: O índice do `output_buffers` do nó de origem (geralmente `0` para a saída principal).
- `dest`: O `name` do nó de destino.
- `dest_port`: O índice do `input_buffers` do nó de destino.

## Exemplo Completo (`test_graph.json`)
```json
{
    "nodes": [
        { "name": "Osc_A", "type": "SineOscillator", "parameters": { "frequency": 440.0 } },
        { "name": "Osc_B", "type": "SineOscillator", "parameters": { "frequency": 220.0 } },
        { "name": "Mixer", "type": "Add" },
        { "name": "RingMod", "type": "Multiply" }
    ],
    "edges": [
        { "source": "Osc_A", "source_port": 0, "dest": "Mixer", "dest_port": 0 },
        { "source": "Osc_B", "source_port": 0, "dest": "Mixer", "dest_port": 1 },
        { "source": "Osc_A", "source_port": 0, "dest": "RingMod", "dest_port": 0 },
        { "source": "Osc_B", "source_port": 0, "dest": "RingMod", "dest_port": 1 }
    ]
}
```

## Como carregar no Python
No seu orquestrador, chame o `GraphLoader` ANTES de chamar `prepare_engine()`:

```python
import dsp2._dsp2_core as core
from dsp2.graph_loader import GraphLoader

engine = core.Engine()
engine.set_signal_parameters(44100.0, 256)

# 1. Carrega a topologia do JSON
GraphLoader.load_from_json(engine, 'test_graph.json')

# 2. Compila o grafo no C++ (resolve topologia e aloca memória Zero-Copy)
engine.prepare_engine()

# 3. Roda o ciclo principal
# for _ in range(blocos): engine.process_block()
```