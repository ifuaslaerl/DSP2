#pragma once

#include "../core/buffer_ops.hpp"
#include "../core/node_base.hpp"
#include "../core/node_factory.hpp"

/**
 * @class HarmonicPitchDetector
 * @brief Estima uma fundamental monofonica provavel a partir de potencia espectral.
 * @note Entradas: Porta 0 (Potencia por bin), Porta 1 (Frequencia em Hz por bin)
 *       Saidas: Porta 0 (Frequencia fundamental em Hz), Porta 1 (Confianca 0..1)
 *       Parametros: "min_midi_note", "max_midi_note", "harmonic_count",
 *                   "relative_threshold", "min_confidence"
 */
template <typename T>
class HarmonicPitchDetector : public NodeBase<T> {
private:
    int min_midi_note = 36;
    int max_midi_note = 84;
    int harmonic_count = 6;
    T relative_threshold = static_cast<T>(0.05);
    T min_confidence = static_cast<T>(0.2);

    int candidate_count = 0;
    T* candidate_frequencies = nullptr;
    T* harmonic_weights = nullptr;

    static T abs_value(T value) {
        return value >= static_cast<T>(0) ? value : -value;
    }

    static T midi_note_to_frequency(int midi_note) {
        T frequency = static_cast<T>(440.0);
        int steps = midi_note - 69;
        const T semitone_up = static_cast<T>(1.0594630943592953);
        const T semitone_down = static_cast<T>(0.9438743126816935);

        while (steps > 0) {
            frequency *= semitone_up;
            --steps;
        }
        while (steps < 0) {
            frequency *= semitone_down;
            ++steps;
        }
        return frequency;
    }

    int nearest_bin_for_frequency(const T* __restrict frequencies, int size, T target) const {
        int best_bin = -1;
        T best_distance = static_cast<T>(0);

        for (int bin = 1; bin < size; ++bin) {
            const T frequency = frequencies[bin];
            if (frequency <= static_cast<T>(0)) {
                continue;
            }

            const T distance = abs_value(frequency - target);
            if (best_bin < 0 || distance < best_distance) {
                best_bin = bin;
                best_distance = distance;
            }
        }

        if (best_bin < 0) {
            return -1;
        }

        T tolerance = static_cast<T>(0);
        if (best_bin > 0) {
            tolerance = abs_value(frequencies[best_bin] - frequencies[best_bin - 1]);
        }
        if (best_bin + 1 < size) {
            const T right_distance = abs_value(frequencies[best_bin + 1] - frequencies[best_bin]);
            if (right_distance > tolerance) {
                tolerance = right_distance;
            }
        }
        tolerance *= static_cast<T>(0.75);
        const T relative_tolerance = target * static_cast<T>(0.03);
        if (relative_tolerance > static_cast<T>(0) && relative_tolerance < tolerance) {
            tolerance = relative_tolerance;
        }
        if (tolerance > static_cast<T>(0) && best_distance > tolerance) {
            return -1;
        }

        return best_bin;
    }

public:
    HarmonicPitchDetector() {
        this->input_buffers.resize(2, nullptr);
        this->output_buffers.resize(2, nullptr);

        this->input_block_sizes.resize(2, 0);
        this->output_block_sizes.resize(2, 0);
        this->input_sample_rates.resize(2, 0.0);
        this->output_sample_rates.resize(2, 0.0);
    }

    void set_parameter(const std::string& param_name, double value) override {
        if (param_name == "min_midi_note") {
            min_midi_note = value > 0.0 ? static_cast<int>(value) : 0;
        } else if (param_name == "max_midi_note") {
            max_midi_note = value > 0.0 ? static_cast<int>(value) : 0;
        } else if (param_name == "harmonic_count") {
            harmonic_count = value > 0.0 ? static_cast<int>(value) : 1;
        } else if (param_name == "relative_threshold") {
            relative_threshold = value > 0.0 ? static_cast<T>(value) : static_cast<T>(0.0);
        } else if (param_name == "min_confidence") {
            min_confidence = value > 0.0 ? static_cast<T>(value) : static_cast<T>(0.0);
        }
    }

    void compute_dimensions() override {
        if (min_midi_note < 0) {
            min_midi_note = 0;
        }
        if (max_midi_note > 127) {
            max_midi_note = 127;
        }
        if (max_midi_note < min_midi_note) {
            max_midi_note = min_midi_note;
        }
        if (harmonic_count < 1) {
            harmonic_count = 1;
        }

        candidate_count = (max_midi_note - min_midi_note) + 1;
        this->output_block_sizes[0] = 1;
        this->output_block_sizes[1] = 1;
        this->output_sample_rates[0] = this->input_sample_rates[0];
        this->output_sample_rates[1] = this->input_sample_rates[0];
    }

    void prepare() override {
        this->output_buffers[0] = new T[this->output_block_sizes[0]];
        this->output_buffers[1] = new T[this->output_block_sizes[1]];
        candidate_frequencies = new T[candidate_count];
        harmonic_weights = new T[harmonic_count];

        for (int i = 0; i < candidate_count; ++i) {
            candidate_frequencies[i] = midi_note_to_frequency(min_midi_note + i);
        }
        for (int harmonic = 0; harmonic < harmonic_count; ++harmonic) {
            harmonic_weights[harmonic] = static_cast<T>(1.0 / static_cast<double>(harmonic + 1));
        }
    }

    void process() override {
        const T* __restrict powers = this->input_buffers[0];
        const T* __restrict frequencies = this->input_buffers[1];
        T* __restrict out_frequency = this->output_buffers[0];
        T* __restrict out_confidence = this->output_buffers[1];

        out_frequency[0] = static_cast<T>(0);
        out_confidence[0] = static_cast<T>(0);

        if (!powers || !frequencies) {
            return;
        }

        const int power_size = this->input_block_sizes[0];
        const int frequency_size = this->input_block_sizes[1];
        const int size = power_size < frequency_size ? power_size : frequency_size;
        if (size < 3) {
            return;
        }

        T max_power = static_cast<T>(0);
        T active_power = static_cast<T>(0);
        for (int bin = 1; bin < size; ++bin) {
            const T power = powers[bin];
            if (power > max_power) {
                max_power = power;
            }
        }

        if (max_power <= static_cast<T>(0)) {
            return;
        }

        const T power_threshold = max_power * relative_threshold;
        for (int bin = 1; bin < size; ++bin) {
            if (powers[bin] >= power_threshold) {
                active_power += powers[bin];
            }
        }

        if (active_power <= static_cast<T>(0)) {
            return;
        }

        int best_candidate = -1;
        T best_score = static_cast<T>(0);
        T best_confidence_score = static_cast<T>(0);
        for (int candidate = 0; candidate < candidate_count; ++candidate) {
            const T fundamental = candidate_frequencies[candidate];
            T score = static_cast<T>(0);
            int matched_harmonics = 0;

            for (int harmonic = 0; harmonic < harmonic_count; ++harmonic) {
                const T target = fundamental * static_cast<T>(harmonic + 1);
                const int bin = nearest_bin_for_frequency(frequencies, size, target);
                if (bin < 0) {
                    continue;
                }

                const T power = powers[bin];
                if (power >= power_threshold) {
                    score += power * harmonic_weights[harmonic];
                    ++matched_harmonics;
                }
            }

            const T coverage = static_cast<T>(
                static_cast<double>(matched_harmonics) / static_cast<double>(harmonic_count)
            );
            const T selection_score = score * coverage;
            if (selection_score > best_score) {
                best_score = selection_score;
                best_confidence_score = score;
                best_candidate = candidate;
            }
        }

        if (best_candidate < 0) {
            return;
        }

        T confidence = best_confidence_score / active_power;
        if (confidence > static_cast<T>(1)) {
            confidence = static_cast<T>(1);
        }

        if (confidence < min_confidence) {
            return;
        }

        out_frequency[0] = candidate_frequencies[best_candidate];
        out_confidence[0] = confidence;
    }

    ~HarmonicPitchDetector() {
        delete[] this->output_buffers[0];
        delete[] this->output_buffers[1];
        delete[] candidate_frequencies;
        delete[] harmonic_weights;
    }
};
