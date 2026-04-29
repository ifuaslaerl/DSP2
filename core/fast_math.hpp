#pragma once
#include <vector>
#include <cmath> // Permitido apenas para inicialização, NUNCA no loop RT
#include "constants.hpp"

namespace DSP2FastMath {
    /**
     * @brief Tabela de pesquisa (Lookup Table) para geração rápida de ondas senoide.
     */
    template <typename T>
    class SineLUT {
    private:
        std::vector<T> table;
        int size;

    public:
        /**
         * @brief Construtor que inicializa a tabela.
         * @param table_size Tamanho da tabela (usa o padrão global se não especificado).
         */
        SineLUT(int table_size = DSP2Config::SINE_LUT_DEFAULT_SIZE) : size(table_size) {
            table.resize(size);
            
            // O cálculo pesado com std::sin ocorre apenas uma vez no setup
            for (int i = 0; i < size; ++i) {
                table[i] = static_cast<T>(std::sin(2.0 * DSP2Config::PI * i / size));
            }
        }

        /**
         * @brief Obtém o valor da senoide sem cálculos trigonométricos.
         * Utiliza inline para evitar overhead de chamada de função no loop de áudio.
         */
        inline T get_value(T phase_index) const {
            int index = static_cast<int>(phase_index) % size;
            if (index < 0) index += size; // Prevenção de índice negativo
            return table[index];
        }

        inline int get_size() const { 
            return size; 
        }
    };
}