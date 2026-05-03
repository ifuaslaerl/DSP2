#pragma once
#include "../core/node_base.hpp"
#include "../core/node_factory.hpp"
#include <cmath> // Permitido apenas no prepare()

/**
 * @class ButterworthFilter
 * @brief Filtro IIR de 2ª Ordem Maximamente Plano.
 * @note Entradas: Porta 0 (Áudio) | Saídas: Porta 0
 */
template <typename T>
class ButterworthFilter : public NodeBase<T> {
private:
    T cutoff = 1000.0;
    int filter_type = 0; // 0 = LowPass, 1 = HighPass
    
    // Coeficientes calculados
    T b0 = 0.0, b1 = 0.0, b2 = 0.0;
    T a1 = 0.0, a2 = 0.0;
    
    // Memória de estado (Z-domain)
    T z1 = 0.0, z2 = 0.0;

public:
    ButterworthFilter() {
        this->input_buffers.resize(1, nullptr);
        this->output_buffers.resize(1, nullptr);
        this->input_block_sizes.resize(1, 0);
        this->output_block_sizes.resize(1, 0);
        this->input_sample_rates.resize(1, 0.0);
        this->output_sample_rates.resize(1, 0.0);
    }

    void set_parameter(const std::string& param_name, double value) override {
        if (param_name == "cutoff") cutoff = static_cast<T>(value);
        else if (param_name == "type") filter_type = static_cast<int>(value);
    }

    void compute_dimensions() override {
        if (this->input_block_sizes[0] > 0) {
            this->output_block_sizes[0] = this->input_block_sizes[0];
            this->output_sample_rates[0] = this->input_sample_rates[0];
        }
    }

    void prepare() override {
        this->output_buffers[0] = new T[this->output_block_sizes[0]];
        z1 = z2 = 0.0; // Reset de estado

        // --- CÁLCULO DOS COEFICIENTES (Fora do tempo real) ---
        double sr = this->output_sample_rates[0];
        if (sr <= 0) sr = DSP2Config::DEFAULT_SAMPLE_RATE;

        double w0 = 2.0 * DSP2Config::PI * cutoff / sr;
        double cos_w0 = std::cos(w0);
        double alpha = std::sin(w0) / (2.0 * 0.70710678118); // Q para Butterworth (1/sqrt(2))

        double a0;
        if (filter_type == 0) { // Low-Pass
            b0 = static_cast<T>((1.0 - cos_w0) / 2.0);
            b1 = static_cast<T>(1.0 - cos_w0);
            b2 = static_cast<T>((1.0 - cos_w0) / 2.0);
            a0 = 1.0 + alpha;
            a1 = static_cast<T>(-2.0 * cos_w0);
            a2 = static_cast<T>(1.0 - alpha);
        } else { // High-Pass
            b0 = static_cast<T>((1.0 + cos_w0) / 2.0);
            b1 = static_cast<T>(-(1.0 + cos_w0));
            b2 = static_cast<T>((1.0 + cos_w0) / 2.0);
            a0 = 1.0 + alpha;
            a1 = static_cast<T>(-2.0 * cos_w0);
            a2 = static_cast<T>(1.0 - alpha);
        }

        // Normalização pelo coeficiente a0
        b0 /= a0; b1 /= a0; b2 /= a0;
        a1 /= a0; a2 /= a0;
    }

    void process() override {
        const T* __restrict in = this->input_buffers[0];
        T* __restrict out = this->output_buffers[0];
        if (!in) return;

        int size = this->output_block_sizes[0];
        
        // Transposed Direct Form II - Altamente otimizado para SIMD e FPU
        for (int i = 0; i < size; ++i) {
            T val = in[i];
            T res = (b0 * val) + z1;
            z1 = (b1 * val) - (a1 * res) + z2;
            z2 = (b2 * val) - (a2 * res);
            out[i] = res;
        }
    }

    ~ButterworthFilter() { delete[] this->output_buffers[0]; }
};