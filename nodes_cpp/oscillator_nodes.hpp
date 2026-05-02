#pragma once

#include "../core/node_base.hpp"
#include "../core/node_factory.hpp"
#include "../core/fast_math.hpp"
#include "../core/constants.hpp"

template <typename T>
class SineOscillator : public NodeBase<T> {
private:
    int currentBlockSize = DSP2Config::DEFAULT_BLOCK_SIZE;
    double sampleRate = DSP2Config::DEFAULT_SAMPLE_RATE;
    DSP2FastMath::SineLUT<T> lut;
    
    // Parâmetros Estáticos (Modificáveis via Python/JSON)
    T baseFrequency = static_cast<T>(440.0);
    T currentPhase = static_cast<T>(0.0);

public:
    SineOscillator() {
        // [Porta 0] Modulação de Frequência (FM) - Opcional
        // [Porta 1] Modulação de Fase (PM) - Opcional
        this->input_buffers.resize(2, nullptr);
        this->output_buffers.resize(1, nullptr);
    }

    // Recebe o parâmetro injetado pelo Python
    void set_parameter(const std::string& param_name, double value) override {
        if (param_name == "frequency") {
            baseFrequency = static_cast<T>(value);
        } else if (param_name == "phase") {
            currentPhase = static_cast<T>(value);
        }
    }

    void prepare(double sr, int bs) override {
        sampleRate = sr;
        currentBlockSize = bs;
        this->output_buffers[0] = new T[currentBlockSize];
    }

    void process() override {
        const T* __restrict freq_in = this->input_buffers[0];
        const T* __restrict phase_in = this->input_buffers[1];
        T* __restrict out = this->output_buffers[0];

        T size_f = static_cast<T>(lut.get_size());
        T freq_to_inc = static_cast<T>(size_f / sampleRate);

        for (int i = 0; i < currentBlockSize; ++i) {
            // 1. Frequência = Parâmetro Base + Entrada Dataflow (FM)
            T current_freq = baseFrequency;
            if (freq_in) current_freq += freq_in[i];
            
            T current_inc = current_freq * freq_to_inc;

            // 2. Fase = Fase Atual + Entrada Dataflow (PM)
            T phase_offset = static_cast<T>(0.0);
            if (phase_in) phase_offset = phase_in[i];

            T modulated_phase = currentPhase + phase_offset;
            
            // Segurança circular da fase
            while (modulated_phase >= size_f) modulated_phase -= size_f;
            while (modulated_phase < 0) modulated_phase += size_f;

            // 3. Lê da Tabela e escreve na saída
            out[i] = lut.get_value(modulated_phase);

            // 4. Avança o motor do tempo
            currentPhase += current_inc;
            if (currentPhase >= size_f) currentPhase -= size_f;
            else if (currentPhase < 0) currentPhase += size_f; // Suporta FM negativa (Thru-Zero)
        }
    }

    ~SineOscillator() { delete[] this->output_buffers[0]; }
};