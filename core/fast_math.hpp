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

    /**
     * @brief Conversor de frequencia em Hz para nota MIDI inteira mais proxima.
     *
     * As fronteiras entre semitons sao calculadas na construcao, fora do ciclo
     * critico. O lookup em tempo real usa apenas comparacoes deterministicas.
     */
    template <typename T>
    class FrequencyToMidiNoteLUT {
    private:
        T boundaries[127];

    public:
        FrequencyToMidiNoteLUT() {
            for (int note = 0; note < 127; ++note) {
                const double boundary_note = static_cast<double>(note) + 0.5;
                boundaries[note] = static_cast<T>(
                    440.0 * std::pow(2.0, (boundary_note - 69.0) / 12.0)
                );
            }
        }

        inline T get_note(T frequency) const {
            if (frequency <= static_cast<T>(0)) {
                return static_cast<T>(0);
            }

            for (int note = 0; note < 127; ++note) {
                if (frequency < boundaries[note]) {
                    return static_cast<T>(note);
                }
            }

            return static_cast<T>(127);
        }
    };
}
