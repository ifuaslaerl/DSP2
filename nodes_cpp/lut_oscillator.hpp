#pragma once
#include "../core/node_base.hpp"
#include "../core/fast_math.hpp"
#include "../core/constants.hpp"

template <typename T>
class LutOscillator : public NodeBase<T> {
private:
    T frequency;
    T phase_index;
    T phase_increment;
    int current_block_size;
    
    // Instância da LUT que pertence ao estado deste nó (Autocontido)
    DSP2FastMath::SineLUT<T> sine_lut;

public:
    LutOscillator(T freq) 
        : frequency(freq), 
          phase_index(0), 
          sine_lut(DSP2Config::SINE_LUT_DEFAULT_SIZE) 
    {
        // 1 Saída, 0 Entradas (Nó Fonte)
        this->output_buffers.resize(1, nullptr);
    }

    void prepare(double sampleRate, int blockSize) override {
        current_block_size = blockSize;
        
        // Alocação de memória para o buffer de saída permitida aqui
        this->output_buffers[0] = new T[blockSize];
        
        // O cálculo do incremento da fase acontece apenas no setup
        phase_increment = static_cast<T>((frequency * sine_lut.get_size()) / sampleRate);
    }

    void process() override {
        // LOOP DE ÁUDIO CRÍTICO
        // 1. PROIBIDO: std::sin, std::exp (Usamos a SineLUT)
        // 2. PROIBIDO: throw, try/catch
        // 3. PROIBIDO: new, malloc, std::vector
        
        T* out = this->output_buffers[0];
        const int lut_size = sine_lut.get_size();
        
        for (int i = 0; i < current_block_size; ++i) {
            out[i] = sine_lut.get_value(phase_index);
            
            // Avança a fase
            phase_index += phase_increment;
            
            // Wrap-around sem usar fmod() da <cmath>
            while (phase_index >= lut_size) {
                phase_index -= lut_size;
            }
        }
        
        #ifndef DSP2_EMBEDDED_MODE
        // Futuro local para profiling e logs pro Python
        #endif
    }
    
    ~LutOscillator() override {
        if (this->output_buffers[0] != nullptr) {
            delete[] this->output_buffers[0];
        }
    }
};