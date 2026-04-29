#pragma once
#include <cmath>

/**
 * @brief Namespace para constantes globais de configuração do D(SP)^2.
 */
namespace DSP2Config {
    // Definição de Pi utilizando acos(-1) para máxima precisão do compilador
    inline const double PI = std::acos(-1.0);

    // Parâmetros de Áudio Padrão
    inline constexpr double DEFAULT_SAMPLE_RATE = 44100.0;
    inline constexpr int DEFAULT_BLOCK_SIZE = 256;

    // Configurações de Fast Math e LUTs
    // Aumentar este valor melhora a fidelidade sonora mas consome mais memória RAM
    inline constexpr int SINE_LUT_DEFAULT_SIZE = 2048;
}