#include "engine.hpp"

// ==========================================
// Construtor e Destrutor
// ==========================================

template <typename T>
Engine<T>::Engine() : sampleRate(DSP2Config::DEFAULT_SAMPLE_RATE), blockSize(DSP2Config::DEFAULT_BLOCK_SIZE) {
    // Instancia o grafo principal do motor
    graph = new Graph<T>();
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

// ==========================================
// Instanciação Explícita de Templates (Garante o linking)
// ==========================================
template class Engine<double>; // Para uso em SIMULATION (Python bindings)
template class Engine<float>;  // Para uso em EMBEDDED (Microcontroladores)