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
        // O Graph e dono dos ponteiros em nodes e os libera no destrutor.
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
        Graph(const Graph&) = delete;
        Graph& operator=(const Graph&) = delete;
        ~Graph();

        // ==========================================
        // Construção do Grafo (Fase de Setup)
        // ==========================================

        /**
         * @brief Adiciona um no ao grafo e transfere ownership para o Graph.
         *
         * O ponteiro deve apontar para um no alocado dinamicamente. Apos esta
         * chamada, o chamador nao deve liberar nem reutilizar o ponteiro como owner.
         */
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

        // Adição para a Fase 3.3
        int get_node_count() const { return nodes.size(); }

        // Retorna o ponteiro bruto da saída de um nó específico
        const T* get_node_output_buffer(int node_id, int port) const {
            if (node_id >= 0 && static_cast<size_t>(node_id) < nodes.size() && 
                port >= 0 && static_cast<size_t>(port) < nodes[node_id]->output_buffers.size()) {
                return nodes[node_id]->output_buffers[port];
            }
            return nullptr;
        }

        int get_node_output_size(int node_id, int port) const {
            if (node_id >= 0 && static_cast<size_t>(node_id) < nodes.size() && 
                port >= 0 && static_cast<size_t>(port) < nodes[node_id]->output_block_sizes.size()) {
                return nodes[node_id]->output_block_sizes[port];
            }
            return 0;
        }

        void set_node_parameter(int node_id, const std::string& param_name, double value) {
            if (node_id >= 0 && static_cast<size_t>(node_id) < nodes.size()) {
                nodes[node_id]->set_parameter(param_name, value);
            }
        }

        void set_node_parameter_array(int node_id, const std::string& param_name, const std::vector<double>& values) {
            if (node_id >= 0 && static_cast<size_t>(node_id) < nodes.size()) {
                nodes[node_id]->set_parameter_array(param_name, values);
            }
        }

        // Retorna a taxa de amostragem física alocada para a saída de um nó
        double get_node_output_sample_rate(int node_id, int port) const {
            if (node_id >= 0 && static_cast<size_t>(node_id) < nodes.size() && 
                port >= 0 && static_cast<size_t>(port) < nodes[node_id]->output_sample_rates.size()) {
                return nodes[node_id]->output_sample_rates[port];
            }
            return 0.0;
        }
};
