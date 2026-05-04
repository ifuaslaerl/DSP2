#pragma once

#include "../core/buffer_ops.hpp"
#include "../core/fft.hpp"
#include "../core/logger.hpp"
#include "../core/node_base.hpp"
#include "../core/node_factory.hpp"

/**
 * @class SpectrumAnalyser
 * @brief Calcula o espectro one-sided de potencia de um bloco de audio real.
 * @note Entradas: Porta 0 (Audio)
 *       Saidas: Porta 0 (Potencia por bin), Porta 1 (Frequencia em Hz por bin)
 *       Parametros: "fft_size" (opcional, ajustado para power-of-two seguro)
 */
template <typename T>
class SpectrumAnalyser : public NodeBase<T> {
private:
    int requested_fft_size = 0;
    int resolved_fft_size = 0;
    int bin_count = 0;
    DSP2FFT::RealFFTPlan<T> fft_plan;

public:
    SpectrumAnalyser() {
        this->input_buffers.resize(1, nullptr);
        this->output_buffers.resize(2, nullptr);

        this->input_block_sizes.resize(1, 0);
        this->output_block_sizes.resize(2, 0);
        this->input_sample_rates.resize(1, 0.0);
        this->output_sample_rates.resize(2, 0.0);
    }

    void set_parameter(const std::string& param_name, double value) override {
        if (param_name == "fft_size") {
            requested_fft_size = value > 0.0 ? static_cast<int>(value) : 0;
        }
    }

    void compute_dimensions() override {
        const int input_size = this->input_block_sizes[0];
        const int target_size =
            requested_fft_size > input_size ? requested_fft_size : input_size;

        resolved_fft_size = DSP2FFT::next_power_of_two(target_size);
        bin_count = (resolved_fft_size / 2) + 1;

        this->output_block_sizes[0] = bin_count;
        this->output_block_sizes[1] = bin_count;
        this->output_sample_rates[0] = this->input_sample_rates[0];
        this->output_sample_rates[1] = this->input_sample_rates[0];
    }

    void prepare() override {
        this->output_buffers[0] = new T[this->output_block_sizes[0]];
        this->output_buffers[1] = new T[this->output_block_sizes[1]];

        if (!fft_plan.configure(resolved_fft_size)) {
            DSP2_LOG_ERROR("SpectrumAnalyser: tamanho de FFT invalido.");
            return;
        }

        const double sample_rate = this->input_sample_rates[0] > 0.0
            ? this->input_sample_rates[0]
            : DSP2Config::DEFAULT_SAMPLE_RATE;

        T* __restrict frequencies = this->output_buffers[1];
        for (int bin = 0; bin < bin_count; ++bin) {
            frequencies[bin] = static_cast<T>(
                static_cast<double>(bin) * sample_rate / static_cast<double>(resolved_fft_size)
            );
        }
    }

    void process() override {
        const T* __restrict input = this->input_buffers[0];
        T* __restrict power = this->output_buffers[0];

        if (!input) {
            DSP2BufferOps::clear(power, bin_count);
            return;
        }

        if (!fft_plan.execute(input, this->input_block_sizes[0])) {
            DSP2BufferOps::clear(power, bin_count);
            return;
        }

        const T normalizer = static_cast<T>(
            1.0 / (static_cast<double>(resolved_fft_size) * static_cast<double>(resolved_fft_size))
        );

        for (int bin = 0; bin < bin_count; ++bin) {
            const T real = fft_plan.real(bin);
            const T imag = fft_plan.imag(bin);
            power[bin] = ((real * real) + (imag * imag)) * normalizer;
        }
    }

    ~SpectrumAnalyser() {
        delete[] this->output_buffers[0];
        delete[] this->output_buffers[1];
    }
};
