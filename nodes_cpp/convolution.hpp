#pragma once
#include "../core/node_base.hpp"
#include "../core/node_factory.hpp"

/**
 * @class Convolution
 * @brief Filtro FIR / Convolução com um Kernel Estático (h[n]).
 */
template <typename T>
class Convolution : public NodeBase<T> {
private:
    std::vector<T> impulse_response; // h[n]
    T* history_buffer = nullptr;     // Buffer circular para x[n]
    int history_index = 0;
    int kernel_size = 0;

public:
    Convolution() {
        this->input_buffers.resize(1, nullptr);
        this->output_buffers.resize(1, nullptr);
        this->input_block_sizes.resize(1, 0);
        this->output_block_sizes.resize(1, 0);
        this->input_sample_rates.resize(1, 0.0);
        this->output_sample_rates.resize(1, 0.0);
    }

    // A nova infraestrutura brilha aqui!
    void set_parameter_array(const std::string& param_name, const std::vector<double>& values) override {
        if (param_name == "kernel") {
            impulse_response.clear();
            for (double v : values) {
                impulse_response.push_back(static_cast<T>(v));
            }
            kernel_size = impulse_response.size();
        }
    }

    void compute_dimensions() override {
        if (this->input_block_sizes[0] > 0) {
            this->output_block_sizes[0] = this->input_block_sizes[0];
            this->output_sample_rates[0] = this->input_sample_rates[0];
        }
    }

    void prepare() override {
        this->output_buffers[0] = new T[this->output_block_sizes[0]];
        
        // Aloca o buffer circular para histórico do tamanho do Kernel
        if (kernel_size > 0) {
            history_buffer = new T[kernel_size](); // () garante inicialização com zeros
        }
        history_index = 0;
    }

    void process() override {
        const T* __restrict in = this->input_buffers[0];
        T* __restrict out = this->output_buffers[0];
        
        if (!in || kernel_size == 0) return;

        int block_size = this->output_block_sizes[0];
        const T* __restrict h = impulse_response.data();

        // Convolução estrita no domínio do tempo.
        // O uso do ponteiro '__restrict' ajuda o compilador a vetorizar este duplo-loop (FMA).
        for (int n = 0; n < block_size; ++n) {
            // Insere a nova amostra no buffer circular
            history_buffer[history_index] = in[n];
            
            T sum = 0.0;
            int read_idx = history_index;

            for (int k = 0; k < kernel_size; ++k) {
                sum += h[k] * history_buffer[read_idx];
                read_idx--;
                if (read_idx < 0) read_idx += kernel_size; // Wrapping do buffer circular
            }

            out[n] = sum;
            
            history_index++;
            if (history_index >= kernel_size) history_index = 0;
        }
    }

    ~Convolution() {
        delete[] this->output_buffers[0];
        delete[] history_buffer;
    }
};