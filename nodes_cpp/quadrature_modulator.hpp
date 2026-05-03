#pragma once
#include "../core/node_base.hpp"
#include "../core/node_factory.hpp"
#include "../core/fast_math.hpp"

/**
 * @class QuadratureModulator
 * @brief Modulador I/Q e Rádio. Multiplica o sinal por Cosseno (I) e Seno (Q).
 * @note Entradas: Porta 0 (Sinal Principal)
 *       Saídas: Porta 0 (In-Phase / I), Porta 1 (Quadrature / Q)
 */
template <typename T>
class QuadratureModulator : public NodeBase<T> {
private:
    T carrier_freq = 1000.0;
    T current_phase = 0.0;
    DSP2FastMath::SineLUT<T> lut;

public:
    QuadratureModulator() {
        this->input_buffers.resize(1, nullptr);
        this->output_buffers.resize(2, nullptr); // DUAS SAÍDAS!
        
        this->input_block_sizes.resize(1, 0);
        this->output_block_sizes.resize(2, 0);
        this->input_sample_rates.resize(1, 0.0);
        this->output_sample_rates.resize(2, 0.0);
    }

    void set_parameter(const std::string& param_name, double value) override {
        if (param_name == "frequency") carrier_freq = static_cast<T>(value);
    }

    void compute_dimensions() override {
        if (this->input_block_sizes[0] > 0) {
            // Propaga a dimensão para AMBAS as saídas
            for(int i = 0; i < 2; i++) {
                this->output_block_sizes[i] = this->input_block_sizes[0];
                this->output_sample_rates[i] = this->input_sample_rates[0];
            }
        }
    }

    void prepare() override {
        this->output_buffers[0] = new T[this->output_block_sizes[0]];
        this->output_buffers[1] = new T[this->output_block_sizes[1]];
        current_phase = 0.0;
    }

    void process() override {
        const T* __restrict in = this->input_buffers[0];
        T* __restrict out_I = this->output_buffers[0]; // Cosseno
        T* __restrict out_Q = this->output_buffers[1]; // Seno

        if (!in) return;

        int size = this->output_block_sizes[0];
        double sr = this->output_sample_rates[0];
        if (sr <= 0) sr = DSP2Config::DEFAULT_SAMPLE_RATE;

        for (int i = 0; i < size; ++i) {
            // Q channel: Seno (Fase normal)
            T q_index = current_phase * lut.get_size();
            T q_carrier = lut.get_value(q_index);

            // I channel: Cosseno (Seno adiantado em 90 graus / 0.25 da fase)
            T i_phase = current_phase + 0.25;
            if (i_phase >= 1.0) i_phase -= 1.0;
            T i_index = i_phase * lut.get_size();
            T i_carrier = lut.get_value(i_index);

            // Modulação (Multiplicação in-place)
            out_Q[i] = in[i] * q_carrier;
            out_I[i] = in[i] * i_carrier;

            // Incremento do oscilador local
            current_phase += carrier_freq / static_cast<T>(sr);
            if (current_phase >= 1.0) current_phase -= 1.0;
        }
    }

    ~QuadratureModulator() {
        delete[] this->output_buffers[0];
        delete[] this->output_buffers[1];
    }
};