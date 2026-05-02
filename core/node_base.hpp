#pragma once

// Para garantir o modo embarcado sem exceções, evitamos bibliotecas padrão pesadas
#include <cstdint>
#include <vector>
#include <string>

// Forward declaration para que o compilador saiba que a classe Graph existe
template <typename T> class Graph;

/**
 * @brief Classe base virtual pura para todos os nós (vértices) de processamento de sinal do DSP2.
 * * Utiliza templates para suportar:
 * - double: Alta precisão para Simulação e prototipagem no Python.
 * - float: Modo EMBEDDED para otimização de performance em microcontroladores.
 */
template <typename T>
class NodeBase {

    // Conceder acesso privilegiado ao Graph
    // Isto permite que a função bind_pointers() aceda aos buffers "protected"
    friend class Graph<T>;

    protected:
        // Múltiplas saídas (onde este nó escreve)
        // O tamanho deste vector é definido no construtor de cada nó específico.
        std::vector<T*> output_buffers;

        // Múltiplas entradas (onde este nó lê - Zero Copy)
        // O motor vai colocar os ponteiros aqui durante a fase compile()
        std::vector<const T*> input_buffers;
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

        // Define um parâmetro interno estático do nó
        virtual void set_parameter(const std::string& /* param_name */, double /* value */) {
            // Método vazio por defeito
        }
};