#pragma once
#include <cstdint>
#include <vector>
#include <string>

template <typename T>
class Graph; // Forward declaration

/**
 * @brief Classe base virtual pura para todos os nós (vértices) de processamento de sinal do DSP2.
 * Agora com suporte a Synchronous Dataflow (SDF) Multirate.
 */
template <typename T>
class NodeBase {
    friend class Graph<T>;

    protected:
        std::vector<T*> output_buffers;
        std::vector<const T*> input_buffers;

        // [NOVO] Propriedades de Multirate (SDF)
        std::vector<int> input_block_sizes;
        std::vector<int> output_block_sizes;
        std::vector<double> input_sample_rates;
        std::vector<double> output_sample_rates;

    public:
        bool is_python_managed = false; // Flag para impedir delete duplo
        virtual ~NodeBase() = default;

        /**
         * @brief [NOVO] Fase 1: Negociação de Dimensões.
         * O nó lê as dimensões que chegaram nas portas de entrada (se houver)
         * e calcula fisicamente o tamanho e a taxa de amostragem de suas saídas.
         */
        virtual void compute_dimensions() = 0;

        /**
         * @brief Fase 2: Alocação e Setup.
         * Único local onde alocação dinâmica é permitida.
         * Agora o nó deve usar o seu próprio `output_block_sizes` para alocar memória,
         * e não mais parâmetros globais.
         */
        virtual void prepare() = 0;

        /**
         * @brief Fase 3: Processamento em Tempo Real.
         * Restrições mantidas: sem new, sem locks, sem exceções.
         */
        virtual void process() = 0;

        virtual void set_parameter(const std::string& /* param_name */, double /* value */) {}

        // Abaixo do set_parameter atual
        virtual void set_parameter_array(const std::string& /* param_name */, const std::vector<double>& /* values */) {}

        // [NOVO] Método para redimensionar os buffers a partir do Python
        void setup_buffers(int num_inputs, int num_outputs) {
            input_buffers.resize(num_inputs, nullptr);
            output_buffers.resize(num_outputs, nullptr);
            input_block_sizes.resize(num_inputs, 256); // 256 como default
            output_block_sizes.resize(num_outputs, 256);
            input_sample_rates.resize(num_inputs, 44100.0);
            output_sample_rates.resize(num_outputs, 44100.0);
        }
};