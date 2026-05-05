#pragma once

#include "../core/buffer_ops.hpp"
#include "../core/node_base.hpp"
#include "../core/node_factory.hpp"

/**
 * @class SpectralPeakPicker
 * @brief Seleciona os picos espectrais mais fortes de um bloco de potencia.
 * @note Entradas: Porta 0 (Potencia por bin), Porta 1 (Frequencia em Hz por bin)
 *       Saidas: Porta 0 (Frequencias selecionadas), Porta 1 (Potencias selecionadas)
 *       Parametros: "peak_count", "min_frequency", "max_frequency", "threshold", "min_bin_distance"
 */
template <typename T>
class SpectralPeakPicker : public NodeBase<T> {
private:
    int peak_count = 6;
    T min_frequency = static_cast<T>(20.0);
    T max_frequency = static_cast<T>(0.0);
    T threshold = static_cast<T>(0.0);
    int min_bin_distance = 1;
    int* selected_bins = nullptr;

    int abs_distance(int left, int right) const {
        return left >= right ? left - right : right - left;
    }

    void remove_selected(int index, int& selected_count) {
        for (int i = index; i < selected_count - 1; ++i) {
            selected_bins[i] = selected_bins[i + 1];
            this->output_buffers[0][i] = this->output_buffers[0][i + 1];
            this->output_buffers[1][i] = this->output_buffers[1][i + 1];
        }
        --selected_count;
    }

    void insert_candidate(int bin, T frequency, T power, int& selected_count) {
        T* __restrict out_frequencies = this->output_buffers[0];
        T* __restrict out_powers = this->output_buffers[1];

        int conflict_index = -1;
        for (int i = 0; i < selected_count; ++i) {
            if (abs_distance(bin, selected_bins[i]) <= min_bin_distance) {
                conflict_index = i;
                break;
            }
        }

        if (conflict_index >= 0) {
            if (power <= out_powers[conflict_index]) {
                return;
            }
            remove_selected(conflict_index, selected_count);
        }

        if (selected_count >= peak_count && power <= out_powers[peak_count - 1]) {
            return;
        }

        int insert_index = selected_count;
        if (insert_index >= peak_count) {
            insert_index = peak_count - 1;
        }

        while (insert_index > 0 && power > out_powers[insert_index - 1]) {
            if (insert_index < peak_count) {
                selected_bins[insert_index] = selected_bins[insert_index - 1];
                out_frequencies[insert_index] = out_frequencies[insert_index - 1];
                out_powers[insert_index] = out_powers[insert_index - 1];
            }
            --insert_index;
        }

        selected_bins[insert_index] = bin;
        out_frequencies[insert_index] = frequency;
        out_powers[insert_index] = power;

        if (selected_count < peak_count) {
            ++selected_count;
        }
    }

public:
    SpectralPeakPicker() {
        this->input_buffers.resize(2, nullptr);
        this->output_buffers.resize(2, nullptr);

        this->input_block_sizes.resize(2, 0);
        this->output_block_sizes.resize(2, 0);
        this->input_sample_rates.resize(2, 0.0);
        this->output_sample_rates.resize(2, 0.0);
    }

    void set_parameter(const std::string& param_name, double value) override {
        if (param_name == "peak_count") {
            peak_count = value > 0.0 ? static_cast<int>(value) : 1;
        } else if (param_name == "min_frequency") {
            min_frequency = value > 0.0 ? static_cast<T>(value) : static_cast<T>(0.0);
        } else if (param_name == "max_frequency") {
            max_frequency = value > 0.0 ? static_cast<T>(value) : static_cast<T>(0.0);
        } else if (param_name == "threshold") {
            threshold = value > 0.0 ? static_cast<T>(value) : static_cast<T>(0.0);
        } else if (param_name == "min_bin_distance") {
            min_bin_distance = value > 0.0 ? static_cast<int>(value) : 0;
        }
    }

    void compute_dimensions() override {
        if (peak_count < 1) {
            peak_count = 1;
        }

        this->output_block_sizes[0] = peak_count;
        this->output_block_sizes[1] = peak_count;
        this->output_sample_rates[0] = this->input_sample_rates[0];
        this->output_sample_rates[1] = this->input_sample_rates[0];
    }

    void prepare() override {
        this->output_buffers[0] = new T[this->output_block_sizes[0]];
        this->output_buffers[1] = new T[this->output_block_sizes[1]];
        this->selected_bins = new int[this->output_block_sizes[0]];
    }

    void process() override {
        const T* __restrict powers = this->input_buffers[0];
        const T* __restrict frequencies = this->input_buffers[1];
        T* __restrict out_frequencies = this->output_buffers[0];
        T* __restrict out_powers = this->output_buffers[1];

        DSP2BufferOps::clear(out_frequencies, peak_count);
        DSP2BufferOps::clear(out_powers, peak_count);
        for (int i = 0; i < peak_count; ++i) {
            selected_bins[i] = -1;
        }

        if (!powers || !frequencies) {
            return;
        }

        const int power_size = this->input_block_sizes[0];
        const int frequency_size = this->input_block_sizes[1];
        const int size = power_size < frequency_size ? power_size : frequency_size;
        if (size < 3) {
            return;
        }

        int selected_count = 0;
        for (int bin = 1; bin < size - 1; ++bin) {
            const T power = powers[bin];
            const T frequency = frequencies[bin];

            if (power <= threshold) continue;
            if (frequency < min_frequency) continue;
            if (max_frequency > static_cast<T>(0.0) && frequency > max_frequency) continue;
            if (!(power > powers[bin - 1] && power > powers[bin + 1])) continue;

            insert_candidate(bin, frequency, power, selected_count);
        }
    }

    ~SpectralPeakPicker() {
        delete[] this->output_buffers[0];
        delete[] this->output_buffers[1];
        delete[] this->selected_bins;
    }
};
