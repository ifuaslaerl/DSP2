#pragma once

#include "graph.hpp"
#include "constants.hpp"

/**
 * @brief O motor principal do DSP2.
 * Serve como interface entre o Grafo de processamento e o mundo exterior 
 */
template <typename T>
class Engine {
private:
    Graph<T>* graph;
    
    // Parâmetros globais de processamento
    double sampleRate;
    int blockSize;

    // TODO: Num futuro próximo, instanciaremos o gestor do Thread Pool aqui
    // ThreadPool* thread_pool;

public:
    Engine();
    ~Engine();

    // ==========================================
    // Configuração
    // ==========================================

    void set_audio_parameters(double sample_rate, int block_size);
    
    // ==========================================
    // Inicialização do Motor
    // ==========================================

    /**
     * @brief Invoca a compilação do Grafo (ordenação topológica e prepare).
     * Deve ser chamado ANTES de iniciar a thread de áudio.
     */
    void prepare_engine();

    // ==========================================
    // Callback de Áudio (Processamento de Bloco)
    // ==========================================
    
    /**
     * @brief Processa exatamente um bloco (blockSize) de dados.
     * No Python, chamamos isto num ciclo while. Num MCU, isto é chamado 
     * pela interrupção (ISR) de hardware (DMA/I2S).
     */
    void process_block();
};