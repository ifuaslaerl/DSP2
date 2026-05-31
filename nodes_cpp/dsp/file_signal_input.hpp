#pragma once
#include "../../core/node_base.hpp"
#include "../../core/node_factory.hpp"

/**
 * @class FileSignalInput
 * @brief Fonte de audio offline alimentada por amostras carregadas no Python.
 * @note Entradas: nenhuma | Saidas: Porta 0
 */
template <typename T>
class FileSignalInput : public NodeBase<T> {
private:
    std::vector<T> samples;
    size_t read_position = 0;
    int hop_size = 0;

public:
    FileSignalInput() {
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

    void set_parameter(const std::string& param_name, double value) override {
        if (param_name == "hop_size") {
            hop_size = value > 0.0 ? static_cast<int>(value) : 0;
        }
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
            const size_t sample_index = read_position + static_cast<size_t>(i);
            if (sample_index < samples.size()) {
                out[i] = samples[sample_index];
            } else {
                out[i] = static_cast<T>(0);
            }
        }

        const int resolved_hop_size = hop_size > 0 ? hop_size : size;
        read_position += static_cast<size_t>(resolved_hop_size);
    }

    ~FileSignalInput() {
        delete[] this->output_buffers[0];
    }
};
