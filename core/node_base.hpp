#pragma once

// Para garantir o modo embarcado sem exceções, evitamos bibliotecas padrão pesadas
#include <cstdint>

/**
 * @brief Classe base virtual pura para todos os nós (vértices) de processamento de sinal do D(SP)^2.
 * * Utiliza templates para suportar:
 * - double: Alta precisão para Simulação e prototipagem no Python.
 * - float: Modo EMBEDDED para otimização de performance em microcontroladores.
 */
template <typename T>
class NodeBase {
public:
    // Destrutor virtual padrão para garantir a correta destruição de classes derivadas
    virtual ~NodeBase() = default;

    /**
     * @brief Prepara o nó antes do início do processamento.
     * * @param sampleRate Taxa de amostragem (ex: 44100.0, 48000.0).
     * @param blockSize Tamanho do buffer de áudio que será processado por ciclo.
     * * REGRA DE ARQUITETURA: Este é o ÚNICO local onde é permitida a alocação dinâmica 
     * de memória (buffers, delay lines, redimensionamento de estruturas).
     */
    virtual void prepare(double sampleRate, int blockSize) = 0;

    /**
     * @brief Função de processamento de áudio (Tempo Real).
     * * REGRA DE ARQUITETURA (Strict Real-Time): 
     * 1. PROIBIDO o uso de alocação dinâmica (new, malloc, std::vector dinâmico).
     * 2. PROIBIDO o uso de bibliotecas matemáticas pesadas da <cmath>.
     * 3. PROIBIDO lançar exceções (throw / try-catch).
     * 4. PROIBIDO locks bloqueantes (mutex) ou I/O (printf, std::cout).
     */
    virtual void process() = 0;
};