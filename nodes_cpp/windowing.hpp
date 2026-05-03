#pragma once
#include "../core/node_base.hpp"
#include "../core/node_factory.hpp"
#include "../core/buffer_ops.hpp"
#include <cmath> // Permitido apenas no prepare()

/**
 * @class Windowing
 * @brief Aplica uma janela matemática estática ao bloco de entrada.
 * @note Entradas: Porta 0 (Sinal) | Saídas: Porta 0 (Sinal Janelado)
 *       Parâmetros: "type" (0 = Hann, 1 = Hamming)
 */
template <typename T>
class Windowing : public NodeBase<T> {
private:
    T* window_buffer = nullptr;
    int window_type = 0; // 0: Hann, 1: Hamming

public:
    Windowing() {
        this->input_buffers.resize(1, nullptr);
        this->output_buffers.resize(1, nullptr);
        
        // Inicializa as propriedades SDF Multirate
        this->input_block_sizes.resize(1, 0);
        this->output_block_sizes.resize(1, 0);
        this->input_sample_rates.resize(1, 0.0);
        this->output_sample_rates.resize(1, 0.0);
    }

    void set_parameter(const std::string& param_name, double value) override {
        if (param_name == "type") window_type = static_cast<int>(value);
    }

    void compute_dimensions() override {
        // O janelamento não altera a taxa de amostragem nem o tamanho do bloco.
        // Apenas propagamos a dimensão da entrada para a saída.
        if (this->input_block_sizes[0] > 0) {
            this->output_block_sizes[0] = this->input_block_sizes[0];
            this->output_sample_rates[0] = this->input_sample_rates[0];
        }
    }

    void prepare() override {
        // Aloca usando a dimensão topológica negociada
        int block_size = this->output_block_sizes[0];
        this->output_buffers[0] = new T[block_size];
        this->window_buffer = new T[block_size];

        // Pré-calcula a janela matemática pesada apenas uma vez (Fase de Setup)
        for (int i = 0; i < block_size; ++i) {
            double multiplier = 1.0;
            
            if (window_type == 0) {
                // Hann Window
                multiplier = 0.5 * (1.0 - std::cos(2.0 * DSP2Config::PI * i / (block_size - 1)));
            } else if (window_type == 1) {
                // Hamming Window
                multiplier = 0.54 - 0.46 * std::cos(2.0 * DSP2Config::PI * i / (block_size - 1));
            }
            
            window_buffer[i] = static_cast<T>(multiplier);
        }
    }

    void process() override {
        const T* __restrict in = this->input_buffers[0];
        T* __restrict out = this->output_buffers[0];

        if (!in) return;

        int block_size = this->output_block_sizes[0];

        // Copia a entrada para a saída e aplica a janela in-place via SIMD
        for (int i = 0; i < block_size; ++i) {
            out[i] = in[i];
        }
        DSP2BufferOps::multiply(out, window_buffer, block_size);
    }

    ~Windowing() {
        delete[] this->output_buffers[0];
        delete[] this->window_buffer;
    }
};