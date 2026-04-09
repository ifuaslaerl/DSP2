# Template Oficial para Nós C++ (D(SP)^2)

**Atenção IAs e Desenvolvedores:** Copiem exatamente esta estrutura ao criar um novo bloco de processamento em `/nodes_cpp/`. Substitua `[NomeDoNo]` pelo nome real.

#pragma once
#include "core/node_base.hpp"
// NOTA: Inclua a API de Fast Math do Core em vez de <cmath>

template <typename T>
class [NomeDoNo] : public NodeBase<T> {
private:
    // Declare as variáveis de estado aqui (sem inicialização dinâmica)

public:
    [NomeDoNo]() {
        // Inicialização básica
    }

    void prepare(double sampleRate, int blockSize) override {
        // Alocação de memória (buffers, delay lines) é PERMITIDA aqui.
    }

    // Função de processamento de áudio crítica
    void process() override { // (Ou T process_sample(), dependendo do design do NodeBase)
        // LOOP DE ÁUDIO CRÍTICO
        // ----------------------------------------------------
        // 1. PROIBIDO: std::sin, std::exp (use Fast Math do core)
        // 2. PROIBIDO: throw, try/catch
        // 3. PROIBIDO: new, malloc, std::vector
        
        #ifndef DSP2_EMBEDDED_MODE
        // Código de profiling ou medição para o Python (ignorado no MCU)
        #endif
    }
};