#pragma once
#include "../core/node_base.hpp"
#include "../core/node_factory.hpp"
#include "../core/fast_math.hpp"

/**
 * @class SineOscillator
 * @brief Gerador de onda senoidal usando LUT e controle de fase contínuo.
 * @note Entradas: Porta 0 (FM Mod), Porta 1 (PM Mod) | Saídas: Porta 0
 */
template <typename T>
class SineOscillator : public NodeBase<T> {
private:
    T base_frequency = 440.0;
    T current_phase = 0.0;
    DSP2FastMath::SineLUT<T> lut; // Instância da Lookup Table do Core

public:
    SineOscillator() {
        // 2 entradas opcionais para modulação, 1 saída principal
        this->input_buffers.resize(2, nullptr);
        this->output_buffers.resize(1, nullptr);
        
        this->input_block_sizes.resize(2, 0);
        this->output_block_sizes.resize(1, 0);
        this->input_sample_rates.resize(2, 0.0);
        this->output_sample_rates.resize(1, 0.0);
    }

    void set_parameter(const std::string& param_name, double value) override {
        if (param_name == "frequency") base_frequency = static_cast<T>(value);
    }

    void compute_dimensions() override {
        // Se houver uma conexão na entrada 0, usamos o block size dela.
        // Se não, o motor (graph.cpp) vai forçar os tamanhos padrão de gerador.
        if (this->input_block_sizes[0] > 0) {
            this->output_block_sizes[0] = this->input_block_sizes[0];
            this->output_sample_rates[0] = this->input_sample_rates[0];
        } else if (this->input_block_sizes[1] > 0) {
            this->output_block_sizes[0] = this->input_block_sizes[1];
            this->output_sample_rates[0] = this->input_sample_rates[1];
        }
    }

    void prepare() override {
        this->output_buffers[0] = new T[this->output_block_sizes[0]];
        current_phase = 0.0; // Reset de fase
    }

    void process() override {
        const T* __restrict fm_in = this->input_buffers[0];
        const T* __restrict pm_in = this->input_buffers[1];
        T* __restrict out = this->output_buffers[0];

        int size = this->output_block_sizes[0];
        double sr = this->output_sample_rates[0];
        
        // Evita divisão por zero se a taxa de amostragem falhar na negociação
        if (sr <= 0.0) sr = DSP2Config::DEFAULT_SAMPLE_RATE;

        for (int i = 0; i < size; ++i) {
            T freq = base_frequency;
            T phase_offset = 0.0;

            if (fm_in) freq += fm_in[i];
            if (pm_in) phase_offset = pm_in[i];

            // Calcula o índice da tabela aplicando a modulação de fase
            T table_index = (current_phase + phase_offset) * lut.get_size();
            out[i] = lut.get_value(table_index);

            // Avança a fase normalizada (0 a 1)
            current_phase += freq / static_cast<T>(sr);
            if (current_phase >= 1.0) current_phase -= 1.0;
            else if (current_phase < 0.0) current_phase += 1.0;
        }
    }

    ~SineOscillator() { delete[] this->output_buffers[0]; }
};