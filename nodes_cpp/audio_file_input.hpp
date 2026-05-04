#pragma once
#include "../core/node_base.hpp"
#include "../core/node_factory.hpp"

/**
 * @class AudioFileInput
 * @brief Fonte de audio offline alimentada por amostras carregadas no Python.
 * @note Entradas: nenhuma | Saidas: Porta 0
 */
template <typename T>
class AudioFileInput : public NodeBase<T> {
private:
    std::vector<T> samples;
    size_t read_position = 0;

public:
    AudioFileInput() {
        this->output_buffers.resize(1, nullptr);
        this->output_block_sizes.resize(1, 0);
        this->output_sample_rates.resize(1, 0.0);
    }

    void set_parameter_array(const std::string& param_name, const std::vector<double>& values) override {
        if (param_name != "samples") return;

        samples.resize(values.size());
        for (size_t i = 0; i < values.size(); ++i) {
            samples[i] = static_cast<T>(values[i]);
        }
        read_position = 0;
    }

    void compute_dimensions() override {
        // Fonte sem entradas: Graph::compile injeta block size e sample rate globais.
    }

    void prepare() override {
        this->output_buffers[0] = new T[this->output_block_sizes[0]];
        read_position = 0;
    }

    void process() override {
        T* __restrict out = this->output_buffers[0];
        int size = this->output_block_sizes[0];

        for (int i = 0; i < size; ++i) {
            if (read_position < samples.size()) {
                out[i] = samples[read_position];
                ++read_position;
            } else {
                out[i] = static_cast<T>(0);
            }
        }
    }

    ~AudioFileInput() {
        delete[] this->output_buffers[0];
    }
};
