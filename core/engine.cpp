#include "engine.hpp"
#include "node_factory.hpp"
#include "../nodes_cpp/dummy_nodes.hpp"

// ==========================================
// Construtor e Destrutor
// ==========================================

template <typename T>
Engine<T>::Engine() : sampleRate(DSP2Config::DEFAULT_SAMPLE_RATE), blockSize(DSP2Config::DEFAULT_BLOCK_SIZE) {
    // Instancia o grafo principal do motor
    graph = new Graph<T>();

    register_core_nodes();
}

template <typename T>
Engine<T>::~Engine() {
    if (graph != nullptr) {
        delete graph;
        graph = nullptr;
    }
}

// ==========================================
// Configuração
// ==========================================

template <typename T>
void Engine<T>::set_audio_parameters(double sample_rate, int block_size) {
    sampleRate = sample_rate;
    blockSize = block_size;
}

// ==========================================
// Inicialização do Motor (Fora do Ciclo Crítico)
// ==========================================

template <typename T>
void Engine<T>::prepare_engine() {
    if (graph != nullptr) {
        // Dispara a ordenação topológica (Kosaraju), avaliação de DAG,
        // alocação de buffers nos nós e mapeamento de ponteiros Zero-Copy.
        graph->compile(sampleRate, blockSize);
    }
}

// ==========================================
// Callback de Áudio (Processamento de Bloco)
// ==========================================

template <typename T>
void Engine<T>::process_block() {
    if (graph != nullptr) {
        // STRICT REAL-TIME: Delega o processamento inteiramente ao Grafo.
        // Nenhuma alocação, lock ou syscall ocorre daqui para a frente.
        graph->process();
    }
}

template <typename T>
int Engine<T>::add_node(const std::string& node_type) {
    // Aloca memória dinamicamente apenas na fase de Setup
    NodeBase<T>* node = NodeFactory<T>::get_instance().create(node_type);
    if (!node) {
        DSP2_LOG_ERROR("NodeFactory: Falha ao criar no - Tipo desconhecido!");
        return -1; // Retorna erro para o Python lidar
    }
    graph->add_node(node);
    return graph->get_node_count() - 1; // Retorna o ID (índice) do nó criado
}

template <typename T>
void Engine<T>::add_edge(int src_id, int src_port, int dest_id, int dest_port) {
    if (graph != nullptr) {
        graph->add_edge(src_id, src_port, dest_id, dest_port);
    }
}

// ==========================================
// Instanciação Explícita de Templates (Garante o linking)
// ==========================================

template class Engine<double>; // Para uso em SIMULATION (Python bindings)
template class Engine<float>;  // Para uso em EMBEDDED (Microcontroladores)