#pragma once
#include <cstdint>
#include "../core/node_base.hpp"
#include "../core/node_factory.hpp"

/**
 * @class NoiseGenerator
 * @brief Gerador de ruido branco pseudoaleatorio uniforme e deterministico.
 * @note Entradas: nenhuma | Saidas: Porta 0
 */
template <typename T>
class NoiseGenerator : public NodeBase<T> {
private:
    static constexpr uint32_t kDefaultSeed = 0x6D2B79F5u;
    static constexpr T kUint32ToUnit = static_cast<T>(1.0 / 4294967295.0);

    T amplitude = static_cast<T>(1.0);
    uint32_t rng_state = kDefaultSeed;

    uint32_t next_random() {
        uint32_t x = rng_state;
        x ^= x << 13;
        x ^= x >> 17;
        x ^= x << 5;
        rng_state = x;
        return x;
    }

public:
    NoiseGenerator() {
        this->output_buffers.resize(1, nullptr);
        this->output_block_sizes.resize(1, 0);
        this->output_sample_rates.resize(1, 0.0);
    }

    void set_parameter(const std::string& param_name, double value) override {
        if (param_name == "amplitude") {
            amplitude = value < 0.0 ? static_cast<T>(0.0) : static_cast<T>(value);
        } else if (param_name == "seed") {
            const uint32_t seed = static_cast<uint32_t>(value);
            rng_state = seed == 0u ? kDefaultSeed : seed;
        }
    }

    void compute_dimensions() override {
        // Gerador sem entradas: as dimensoes sao injetadas pelo Graph.
    }

    void prepare() override {
        this->output_buffers[0] = new T[this->output_block_sizes[0]];
    }

    void process() override {
        T* __restrict out = this->output_buffers[0];
        const int size = this->output_block_sizes[0];
        const T scale = amplitude * static_cast<T>(2.0);

        for (int i = 0; i < size; ++i) {
            const T unit = static_cast<T>(next_random()) * kUint32ToUnit;
            out[i] = (unit * scale) - amplitude;
        }
    }

    ~NoiseGenerator() {
        delete[] this->output_buffers[0];
    }
};
