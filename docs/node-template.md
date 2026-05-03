# Template Oficial para Nós C++ (D(SP)^2)

**Atenção IAs e Desenvolvedores:** Copiem exatamente esta estrutura ao criar um novo bloco de processamento em `/nodes_cpp/`. 
1. Substitua `[NomeDoNo]` pelo nome real do seu módulo.
2. Certifique-se de alocar as portas `input_buffers` e `output_buffers` no construtor.
3. Não esqueça de adicionar o registro na Factory (veja o final do arquivo).

```cpp
#pragma once
#include "../core/node_base.hpp"
#include "../core/node_factory.hpp"
// NOTA: Inclua a API de Fast Math do Core em vez de <cmath>

template <typename T>
class [NomeDoNo] : public NodeBase<T> {
private:
    // Declare as variáveis de estado (ex: fase, delay lines)
public:
    [NomeDoNo]() {
        // Inicialização básica. Exemplo para 2 entradas e 1 saída:
        // this->input_buffers.resize(2, nullptr);
        // this->output_buffers.resize(1, nullptr);
    }

    void prepare(double sampleRate, int blockSize) override {
        // ÚNICO LOCAL onde alocação de memória é PERMITIDA.
        // Ex: this->output_buffers[0] = new T[blockSize];
    }

    // Função de processamento crítica (Tempo Real)
    void process() override {
        // ----------------------------------------------------
        // 1. PROIBIDO: std::sin, std::exp (use Fast Math do core)
        // 2. PROIBIDO: throw, try/catch
        // 3. PROIBIDO: new, malloc, std::vector dinâmico
        // ----------------------------------------------------
        
        // Loop otimizado:
        // int size = DSP2Config::DEFAULT_BLOCK_SIZE;
        // for (int i = 0; i < size; ++i) { ... }
    }

    ~[NomeDoNo]() {
        // Libere a memória alocada no prepare()
        // delete[] this->output_buffers[0];
    }
};

/* 
 * ATENÇÃO AGENTE DE IA: Copie o bloco abaixo e cole dentro da função 
 * `register_core_nodes()` no arquivo `core/engine.cpp` para expor ao Python.
 *
 * NodeFactory<double>::get_instance().register_node("[NomeDoNo]", [](){ return new [NomeDoNo]<double>(); });
 */
```