#pragma once

#include <cmath>
#include <complex>
#include <cstddef>
#include <vector>

#include "constants.hpp"

namespace DSP2FFT {

inline bool is_power_of_two(int value) {
    return value > 0 && (value & (value - 1)) == 0;
}

inline int next_power_of_two(int value) {
    if (value <= 1) return 1;

    int power = 1;
    while (power < value) {
        power <<= 1;
    }
    return power;
}

/**
 * @brief Plano FFT radix-2 para blocos reais.
 *
 * A classe separa a fase de configuracao, onde vetores e twiddles sao
 * alocados, da fase de execucao. Depois de configure(), execute() nao faz
 * alocacao dinamica e pode ser chamado a partir de um no em process().
 */
template <typename T>
class RealFFTPlan {
private:
    int fft_size = 0;
    std::vector<int> bit_reverse;
    std::vector<std::complex<T>> twiddles;
    std::vector<std::complex<T>> work_buffer;

public:
    bool configure(int requested_size) {
        if (!is_power_of_two(requested_size)) {
            return false;
        }

        fft_size = requested_size;
        bit_reverse.resize(static_cast<size_t>(fft_size));
        twiddles.resize(static_cast<size_t>(fft_size / 2));
        work_buffer.resize(static_cast<size_t>(fft_size));

        int bits = 0;
        while ((1 << bits) < fft_size) {
            ++bits;
        }

        for (int i = 0; i < fft_size; ++i) {
            int reversed = 0;
            for (int b = 0; b < bits; ++b) {
                if (i & (1 << b)) {
                    reversed |= 1 << (bits - 1 - b);
                }
            }
            bit_reverse[static_cast<size_t>(i)] = reversed;
        }

        for (int i = 0; i < fft_size / 2; ++i) {
            const double angle = -2.0 * DSP2Config::PI * static_cast<double>(i) /
                                 static_cast<double>(fft_size);
            twiddles[static_cast<size_t>(i)] = std::complex<T>(
                static_cast<T>(std::cos(angle)),
                static_cast<T>(std::sin(angle))
            );
        }

        return true;
    }

    int size() const {
        return fft_size;
    }

    bool execute(const T* input, int input_size) {
        if (fft_size <= 0 || input == nullptr || input_size < 0) {
            return false;
        }

        for (int i = 0; i < fft_size; ++i) {
            const int source_index = bit_reverse[static_cast<size_t>(i)];
            const T value = source_index < input_size ? input[source_index] : static_cast<T>(0);
            work_buffer[static_cast<size_t>(i)] = std::complex<T>(value, static_cast<T>(0));
        }

        for (int length = 2; length <= fft_size; length <<= 1) {
            const int half = length >> 1;
            const int stride = fft_size / length;

            for (int start = 0; start < fft_size; start += length) {
                for (int j = 0; j < half; ++j) {
                    const std::complex<T> twiddle = twiddles[static_cast<size_t>(j * stride)];
                    const std::complex<T> odd =
                        work_buffer[static_cast<size_t>(start + j + half)] * twiddle;
                    const std::complex<T> even = work_buffer[static_cast<size_t>(start + j)];

                    work_buffer[static_cast<size_t>(start + j)] = even + odd;
                    work_buffer[static_cast<size_t>(start + j + half)] = even - odd;
                }
            }
        }

        return true;
    }

    T real(int bin) const {
        return work_buffer[static_cast<size_t>(bin)].real();
    }

    T imag(int bin) const {
        return work_buffer[static_cast<size_t>(bin)].imag();
    }
};

}  // namespace DSP2FFT
