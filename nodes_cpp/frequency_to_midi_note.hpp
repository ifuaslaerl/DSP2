#pragma once

#include "../core/fast_math.hpp"
#include "../core/node_base.hpp"
#include "../core/node_factory.hpp"

/**
 * @class FrequencyToMidiNote
 * @brief Converte frequencias em Hz para notas MIDI inteiras mais proximas.
 * @note Entradas: Porta 0 (Frequencias em Hz)
 *       Saidas: Porta 0 (Notas MIDI)
 */
template <typename T>
class FrequencyToMidiNote : public NodeBase<T> {
private:
    DSP2FastMath::FrequencyToMidiNoteLUT<T> midi_lut;

public:
    FrequencyToMidiNote() {
        this->input_buffers.resize(1, nullptr);
        this->output_buffers.resize(1, nullptr);

        this->input_block_sizes.resize(1, 0);
        this->output_block_sizes.resize(1, 0);
        this->input_sample_rates.resize(1, 0.0);
        this->output_sample_rates.resize(1, 0.0);
    }

    void compute_dimensions() override {
        if (this->input_block_sizes[0] > 0) {
            this->output_block_sizes[0] = this->input_block_sizes[0];
            this->output_sample_rates[0] = this->input_sample_rates[0];
        }
    }

    void prepare() override {
        this->output_buffers[0] = new T[this->output_block_sizes[0]];
    }

    void process() override {
        const T* __restrict frequencies = this->input_buffers[0];
        T* __restrict notes = this->output_buffers[0];

        if (!frequencies) {
            for (int i = 0; i < this->output_block_sizes[0]; ++i) {
                notes[i] = static_cast<T>(0);
            }
            return;
        }

        const int size = this->output_block_sizes[0];
        for (int i = 0; i < size; ++i) {
            notes[i] = midi_lut.get_note(frequencies[i]);
        }
    }

    ~FrequencyToMidiNote() {
        delete[] this->output_buffers[0];
    }
};
