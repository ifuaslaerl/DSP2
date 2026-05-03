#pragma once
#include "../core/node_base.hpp"
#include "../core/node_factory.hpp"

template <typename T>
class Decimator : public NodeBase<T> {
private:
    int factor = 2;

public:
    Decimator() {
        this->input_buffers.resize(1, nullptr);
        this->output_buffers.resize(1, nullptr);
        
        // Inicializa as propriedades SDF
        this->input_block_sizes.resize(1, 0);
        this->output_block_sizes.resize(1, 0);
        this->input_sample_rates.resize(1, 0.0);
        this->output_sample_rates.resize(1, 0.0);
    }

    void set_parameter(const std::string& param_name, double value) override {
        if (param_name == "factor" && value >= 1.0) {
            factor = static_cast<int>(value);
        }
    }

    void compute_dimensions() override {
        // Regra SDF do Decimador: Tamanho e Taxa divididos pelo fator M
        if (this->input_block_sizes[0] > 0) {
            this->output_block_sizes[0] = this->input_block_sizes[0] / factor;
            this->output_sample_rates[0] = this->input_sample_rates[0] / static_cast<double>(factor);
        }
    }

    void prepare() override {
        // Alocação exata do bloco reduzido! Economia massiva de RAM.
        this->output_buffers[0] = new T[this->output_block_sizes[0]];
    }

    void process() override {
        const T* __restrict in = this->input_buffers[0];
        T* __restrict out = this->output_buffers[0];

        if (!in) return;

        int out_size = this->output_block_sizes[0];
        for (int i = 0; i < out_size; ++i) {
            out[i] = in[i * factor]; // Pula fisicamente as amostras
        }
    }

    ~Decimator() {
        delete[] this->output_buffers[0];
    }
};