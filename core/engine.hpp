#pragma once
#include <string>
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

    // ==========================================
    // Orquestração de Grafo
    // ==========================================

    int add_node(const std::string& node_type);
    void add_edge(int src_id, int src_port, int dest_id, int dest_port);

    // Extrai o buffer de um nó e converte para std::vector (fácil de ler no Python)
    std::vector<T> get_node_output(int node_id, int port);

    void set_node_parameter(int node_id, const std::string& param_name, double value);
};