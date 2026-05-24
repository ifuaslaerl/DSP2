#pragma once
#include "../../core/node_base.hpp"
#include "../../core/node_factory.hpp"

/**
 * @class ProbeNode
 * @brief Nó de interceptação (Tap Point).
 * Copia o buffer de entrada para a saída sem alterar o sinal original,
 * permitindo a inspeção de dados intermediários no grafo (Fase 4.3).
 */
template <typename T>
class ProbeNode : public NodeBase<T> {
public:
    ProbeNode() {
        // 1 Entrada, 1 Saída
        this->input_buffers.resize(1, nullptr);
        this->output_buffers.resize(1, nullptr);
        
        this->input_block_sizes.resize(1, 0);
        this->output_block_sizes.resize(1, 0);
        this->input_sample_rates.resize(1, 0.0);
        this->output_sample_rates.resize(1, 0.0);
    }

    void compute_dimensions() override {
        // Herda as dimensões exatas da porta de entrada
        if (this->input_block_sizes[0] > 0) {
            this->output_block_sizes[0] = this->input_block_sizes[0];
            this->output_sample_rates[0] = this->input_sample_rates[0];
        }
    }

    void prepare() override {
        // ÚNICO local onde a alocação de memória é permitida
        this->output_buffers[0] = new T[this->output_block_sizes[0]];
    }

    void process() override {
        const T* __restrict in = this->input_buffers[0];
        T* __restrict out = this->output_buffers[0];

        if (!in || !out) return;

        int size = this->output_block_sizes[0];
        
        // Cópia ponto a ponto otimizada para auto-vetorização (SIMD)
        for (int i = 0; i < size; ++i) {
            out[i] = in[i];
        }
    }

    ~ProbeNode() {
        delete[] this->output_buffers[0];
    }
};