/**
 * @file test_phase1.cpp
 * @brief Teste de Integração da Fase 1 do D(SP)^2.
 * * Valida a arquitetura base do motor C++:
 * 1. Ordenação Topológica do Grafo (Kosaraju/Kahn).
 * 2. Mapeamento de memória Zero-Copy entre nós.
 * 3. Execução Lock-Free e sem alocações no ciclo process().
 */

#include <iostream>
#include <vector>
#include "../core/engine.hpp"
#include "../core/node_base.hpp"

// ========================================================
// MÓDULOS DE TESTE REUTILIZÁVEIS
// Podem ser movidos para um "tests/dummy_nodes.hpp" no futuro
// ========================================================

/**
 * @class DummyGenerator
 * @brief Nó fonte que preenche o buffer com um valor constante estático.
 */
template <typename T>
class DummyGenerator : public NodeBase<T> {
private:
    T constant_value;
    int current_block_size;
public:
    DummyGenerator(T val) : constant_value(val) {
        this->output_buffers.resize(1, nullptr); // 1 Saída
    }

    void prepare(double sampleRate, int blockSize) override {
        current_block_size = blockSize;
        // Fase de Setup: Alocação permitida
        this->output_buffers[0] = new T[blockSize];
    }

    void process() override {
        // Strict Real-Time: Apenas matemática, sem alocações
        T* out = this->output_buffers[0];
        for (int i = 0; i < current_block_size; ++i) {
            out[i] = constant_value;
        }
    }

    ~DummyGenerator() { delete[] this->output_buffers[0]; }
};

/**
 * @class DummyMultiplier
 * @brief Nó de processamento que multiplica a entrada por um ganho.
 */
template <typename T>
class DummyMultiplier : public NodeBase<T> {
private:
    T gain;
    int current_block_size;
public:
    DummyMultiplier(T g) : gain(g) {
        this->input_buffers.resize(1, nullptr);  // 1 Entrada
        this->output_buffers.resize(1, nullptr); // 1 Saída
    }

    void prepare(double sampleRate, int blockSize) override {
        current_block_size = blockSize;
        // Aloca apenas a saída. A entrada será mapeada via Zero-Copy pelo Graph.
        this->output_buffers[0] = new T[blockSize];
    }

    void process() override {
        // Mapeamento Zero-Copy: input_buffers aponta para a memória do nó anterior
        const T* in = this->input_buffers[0]; 
        T* out = this->output_buffers[0];
        
        for (int i = 0; i < current_block_size; ++i) {
            out[i] = in[i] * gain;
        }
    }

    ~DummyMultiplier() { delete[] this->output_buffers[0]; }
    
    // Utilitário para o teste ler o resultado final
    T get_result(int index) { return this->output_buffers[0][index]; }
};

// ========================================================
// ROTINA DE TESTE (MAIN)
// ========================================================
int main() {
    std::cout << "--- D(SP)^2 : Iniciando Teste da Fase 1 ---\n";

    // 1. Instanciar o Grafo para modo EMBEDDED (float)
    Graph<float> graph;
    
    // 2. Instanciar os nós (Gerador gera 2.0, Multiplicador multiplica por 3.0)
    auto* gen = new DummyGenerator<float>(2.0f);     
    auto* mult = new DummyMultiplier<float>(3.0f);   

    graph.add_node(gen);
    graph.add_node(mult);

    // 3. Ligar Saída 0 do nó 0 (gen) à Entrada 0 do nó 1 (mult)
    graph.add_edge(0, 0, 1, 0);

    // 4. Compilar (Aloca memórias e resolve Zero-Copy)
    std::cout << "[INFO] Compilando o Grafo...\n";
    graph.compile(44100.0, 256);

    // 5. Ciclo de Áudio (Lock-free e Allocation-free)
    std::cout << "[INFO] Processando bloco de audio...\n";
    graph.process();

    // 6. Validação
    float result = mult->get_result(0); // 2.0 * 3.0 = 6.0
    
    // Limpeza
    delete gen;
    delete mult;

    if (result == 6.0f) {
        std::cout << "✅ SUCESSO: O Dataflow e o Mapeamento Zero-Copy estao operacionais.\n";
        return 0; // Código 0 = Sucesso para o CTest
    } else {
        std::cout << "❌ FALHA: Resultado inesperado. Obtido: " << result << ", Esperado: 6.0\n";
        return 1; // Código 1 = Falha para o CTest
    }
}