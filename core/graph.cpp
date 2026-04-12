#include "graph.hpp"
#include <queue>

// ==========================================
// Construção do Grafo (Fase de Setup)
// ==========================================

template <typename T>
void Graph<T>::add_node(NodeBase<T>* node) {
    nodes.push_back(node);
}

template <typename T>
void Graph<T>::add_edge(int source_id, int source_port, int dest_id, int dest_port) {
    edges.push_back({source_id, source_port, dest_id, dest_port});
}

// ==========================================
// Kosaraju & Deteção de Ciclos
// ==========================================

template <typename T>
void Graph<T>::build_adjacency_lists(vector<vector<int>>& adj, vector<vector<int>>& adj_rev) {
    adj.assign(nodes.size(), vector<int>());
    adj_rev.assign(nodes.size(), vector<int>());
    
    for (const auto& edge : edges) {
        adj[edge.source_id].push_back(edge.dest_id);
        adj_rev[edge.dest_id].push_back(edge.source_id);
    }
}

template <typename T>
void Graph<T>::dfs1(int v, vector<bool>& visited, stack<int>& finish_stack, const vector<vector<int>>& adj) {
    visited[v] = true;
    for (int neighbor : adj[v]) {
        if (!visited[neighbor]) {
            dfs1(neighbor, visited, finish_stack, adj);
        }
    }
    finish_stack.push(v);
}

template <typename T>
void Graph<T>::dfs2(int v, vector<bool>& visited, vector<int>& component, const vector<vector<int>>& adj_rev) {
    visited[v] = true;
    component.push_back(v);
    for (int neighbor : adj_rev[v]) {
        if (!visited[neighbor]) {
            dfs2(neighbor, visited, component, adj_rev);
        }
    }
}

template <typename T>
void Graph<T>::run_kosaraju() {
    vector<vector<int>> adj, adj_rev;
    build_adjacency_lists(adj, adj_rev);

    int n = nodes.size();
    vector<bool> visited(n, false);
    stack<int> finish_stack;

    // Passo 1: Preencher a stack com a ordem de finalização
    for (int i = 0; i < n; ++i) {
        if (!visited[i]) {
            dfs1(i, visited, finish_stack, adj);
        }
    }

    // Passo 2: Resetar visited e processar o grafo transposto (adj_rev)
    fill(visited.begin(), visited.end(), false);
    sccs.clear();

    while (!finish_stack.empty()) {
        int v = finish_stack.top();
        finish_stack.pop();

        if (!visited[v]) {
            vector<int> component;
            dfs2(v, visited, component, adj_rev);
            sccs.push_back(component);
        }
    }
}

template <typename T>
bool Graph<T>::detect_cycles() {
    // Se algum Componente Fortemente Conexo (SCC) tiver mais de 1 vértice, existe um ciclo.
    for (const auto& component : sccs) {
        if (component.size() > 1) {
            return true;
        }
    }
    
    // Verificação de self-loops (nó ligado a si mesmo)
    for (const auto& edge : edges) {
        if (edge.source_id == edge.dest_id) {
            return true;
        }
    }
    
    return false;
}

template <typename T>
void Graph<T>::resolve_cyclic_graph() {
    // TODO (DISCUTIR POSTERIORMENTE):
    // Como os ciclos de processamento de sinal (feedback loops) serão tratados?
    // Exemplo de solução futura: Inserir automaticamente um nó de atraso (delay unitário z^-1)
    // nas arestas de retorno para quebrar o ciclo topológico sem quebrar o áudio.
}

// ==========================================
// Ordenação Topológica & Bindings
// ==========================================

template <typename T>
void Graph<T>::build_dag_layers() {
    int n = nodes.size();
    vector<int> in_degree(n, 0);
    vector<vector<int>> adj(n, vector<int>());

    for (const auto& edge : edges) {
        adj[edge.source_id].push_back(edge.dest_id);
        in_degree[edge.dest_id]++;
    }

    queue<int> q;
    for (int i = 0; i < n; ++i) {
        if (in_degree[i] == 0) {
            q.push(i);
        }
    }

    execution_layers.clear();

    // Kahn's algorithm adaptado para extrair camadas de paralelismo
    while (!q.empty()) {
        int layer_size = q.size();
        vector<int> current_layer;

        for (int i = 0; i < layer_size; ++i) {
            int u = q.front();
            q.pop();
            current_layer.push_back(u);

            for (int v : adj[u]) {
                if (--in_degree[v] == 0) {
                    q.push(v);
                }
            }
        }
        execution_layers.push_back(current_layer);
    }
}

template <typename T>
void Graph<T>::bind_pointers() {
    // Zero-Copy Mapeamento:
    // O destino (input) aponta diretamente para a memória alocada na origem (output).
    // Nota: Requer que input_buffers e output_buffers sejam acessíveis no NodeBase.
    for (const auto& edge : edges) {
        // Assume-se a existência de métodos setters no NodeBase ou amizade (friend class)
        nodes[edge.dest_id]->input_buffers[edge.dest_port] = nodes[edge.source_id]->output_buffers[edge.source_port];
    }
}

// ==========================================
// Compilação (Onde alocação de memória é permitida)
// ==========================================

template <typename T>
void Graph<T>::compile(double sampleRate, int blockSize) {
    run_kosaraju();

    if (detect_cycles()) {
        resolve_cyclic_graph();
    }

    build_dag_layers();
    
    // Todos os nós alocam as suas memórias locais de forma segura
    for (auto* node : nodes) {
        node->prepare(sampleRate, blockSize);
    }

    bind_pointers();
}

// ==========================================
// Ciclo Crítico de Tempo Real
// ==========================================

template <typename T>
void Graph<T>::process() {
    // STRICT REAL-TIME: Sem alocações (new, malloc) ou syscalls bloqueantes aqui!
    // Percorre cada camada topológica de forma sequencial (futuramente via ThreadPool)
    for (const auto& layer : execution_layers) {
        for (int node_id : layer) {
            nodes[node_id]->process();
        }
    }
}

template <typename T>
Graph<T>::~Graph() {
    // Opcional: Gestão de memória se o Graph for dono dos ponteiros dos nós
}

// ==========================================
// Instanciação Explícita de Templates (Garante o linking)
// ==========================================
template class Graph<double>; // Para uso em SIMULATION (Python bindings)
template class Graph<float>;  // Para uso em EMBEDDED (Microcontroladores)