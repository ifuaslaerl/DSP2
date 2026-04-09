#pragma once

#include <vector>
#include "node_base.hpp"

using namespace std;

/**
 * @brief Estrutura que representa uma ligação (aresta) entre portas de dois vértices.
 */
struct Edge {
    int source_id;   // ID do nó de origem
    int source_port; // QUAL saída do nó de origem
    
    int dest_id;     // ID do nó de destino
    int dest_port;   // QUAL entrada do nó de destino deve receber o sinal
};

/**
 * @brief O motor de orquestração do Dataflow. 
 * Responsável por compilar a ordem de execução e despachar o processamento.
 */
template <typename T>
class Graph {
    private:
        // O armazenamento principal dos nós e das ligações
        vector<NodeBase<T>*> nodes;
        vector<Edge> edges;

        // As camadas de execução topológica para o Thread Pool (Paralelismo)
        // Camada 0 processa primeiro. Camada 1 só processa quando a 0 terminar, etc.
        vector<vector<int>> execution_layers;

        // ==========================================
        // Funções Internas de Compilação (Seguras para alocar)
        // ==========================================

        bool detect_cycles();
        void build_dag_layers();
        void resolve_cyclic_graph();
        
        /**
         * @brief Efetua o mapeamento "Zero-Copy". 
         * Aponta os ponteiros `const T*` de entrada dos nós de destino 
         * diretamente para os buffers de saída dos nós de origem.
         */
        void bind_pointers(); 

    public:
        Graph() = default;
        ~Graph();

        // ==========================================
        // Construção do Grafo (Fase de Setup)
        // ==========================================

        void add_node(NodeBase<T>* node);
        
        /**
         * @brief Adiciona uma ligação entre a porta de saída de um nó e a porta de entrada de outro.
         * @param source_id Índice do nó de origem.
         * @param source_port Índice da saída do nó de origem.
         * @param dest_id Índice do nó de destino.
         * @param dest_port Índice da entrada do nó de destino.
         */
        void add_edge(int source_id, int source_port, int dest_id, int dest_port);

        // ==========================================
        // Preparação (Único local onde alocação é permitida)
        // ==========================================

        void compile(double sampleRate, int blockSize);

        // ==========================================
        // Ciclo Crítico de Tempo Real (Zero-Allocation, Lock-Free)
        // ==========================================
        
        void process();
};