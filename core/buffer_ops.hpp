#pragma once

/**
 * @brief Operações vetorizadas de buffer para alta performance no D(SP)^2.
 * O uso de ponteiros `__restrict` garante que não há aliasing de memória,
 * destravando a vetorização SIMD automática agressiva do compilador (flags -O3).
 */
namespace DSP2BufferOps {

    /**
     * @brief Multiplica dois buffers ponto a ponto (ex: Modulação em Anel / VCA).
     * @param dest Buffer de destino (onde o resultado será gravado e acumulado).
     * @param src Buffer fonte (sinal modulador).
     * @param size Tamanho dos buffers (blockSize).
     */
    template <typename T>
    inline void multiply(T* __restrict dest, const T* __restrict src, int size) {
        for (int i = 0; i < size; ++i) {
            dest[i] *= src[i];
        }
    }

    /**
     * @brief Multiplica um buffer por um escalar estático (ex: Controle de Volume).
     */
    template <typename T>
    inline void multiply_scalar(T* dest, T scalar, int size) {
        for (int i = 0; i < size; ++i) {
            dest[i] *= scalar;
        }
    }

    /**
     * @brief Soma dois buffers ponto a ponto (ex: Mixagem de Sinais).
     */
    template <typename T>
    inline void add(T* __restrict dest, const T* __restrict src, int size) {
        for (int i = 0; i < size; ++i) {
            dest[i] += src[i];
        }
    }

    /**
     * @brief Zera todo o conteúdo de um buffer rapidamente.
     */
    template <typename T>
    inline void clear(T* dest, int size) {
        for (int i = 0; i < size; ++i) {
            dest[i] = static_cast<T>(0);
        }
    }
}