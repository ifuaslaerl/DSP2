#pragma once

#include <vector>
#include <stack>
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
        vector<vector<int>> execution_layers;

        // Armazena os Componentes Fortemente Conexos (SCCs) encontrados
        // Cada sub-vetor contém os IDs dos nós que formam um ciclo fechado
        vector<vector<int>> sccs;

        // ==========================================
        // Funções Internas de Compilação (Seguras para alocar)
        // ==========================================

        // Helpers para o Algoritmo de Kosaraju
        void build_adjacency_lists(vector<vector<int>>& adj, vector<vector<int>>& adj_rev);
        void dfs1(int v, vector<bool>& visited, stack<int>& finish_stack, const vector<vector<int>>& adj);
        void dfs2(int v, vector<bool>& visited, vector<int>& component, const vector<vector<int>>& adj_rev);
        
        /**
         * @brief Executa o Algoritmo de Kosaraju para preencher o vetor sccs.
         */
        void run_kosaraju();

        /**
         * @brief Utiliza os SCCs para verificar se o grafo é um DAG perfeito.
         * Retorna true se houver ciclos (algum SCC com tamanho > 1 ou com self-loop).
         */
        bool detect_cycles();
        
        /**
         * @brief Condensa o grafo agrupando nós de cada SCC e gera a ordenação topológica.
         */
        void build_dag_layers();
        
        /**
         * @brief Trata os nós dentro de um SCC (ex: alocando buffers de atraso/feedback explícito).
         */
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