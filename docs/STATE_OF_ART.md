# 🧠 Arquitetura e Estado da Arte do $D(SP)^2$

O **$D(SP)^2$ (Digital Signal Processing Simulation Program)** é um motor de processamento digital de sinais baseado num fluxo de dados (Dataflow) contínuo e estático. A sua arquitetura híbrida utiliza um *Core* hermético em C++ para processamento de Tempo Real (RT), orquestrado por uma interface flexível em Python baseada em grafos (JSON).

## 1. Princípios Arquiteturais e Regras de Ouro (AGENTS.md)

O sistema foi concebido para ambientes de alta performance e sistemas embarcados. Qualquer desenvolvimento no motor C++ deve respeitar estas restrições inegociáveis:

*   **Separação de Fases (Alocação vs. Tempo Real):**
    *   **Fase de Setup (`prepare()`):** Ocorre durante a inicialização. É o **único** local onde a alocação dinâmica de memória (`new`, `malloc`) é permitida.
    *   **Fase de Processamento (`process()`):** Ocorre no loop de principal. São proibidas invocações ao *heap*, lançamentos de exceções, locks bloqueantes e chamadas à biblioteca `<cmath>`.
*   **Zero-Copy Routing:** Os buffers fluem entre nós por referência. É estritamente proibido um nó alterar o seu `input_buffer`. O roteamento aponta a entrada de destino diretamente para o endereço de saída da origem.
*   **Auto-Vetorização (SIMD):** As operações matemáticas em bloco utilizam ponteiros com o modificador `__restrict`, garantindo que o compilador aplica otimizações vetoriais em paralelo sob a flag `-O3`.

## 2. A Infraestrutura do Motor e Grafo (api.md)

*   **A Classe `NodeBase<T>`:** Todas as unidades de processamento herdam desta base. Ela gere os vetores de entrada (ponteiros constantes) e os buffers de saída. Implementa funções virtuais cruciais: `prepare`, `process` e o mecanismo dinâmico `set_parameter`.
*   **O `Graph<T>` e `Engine<T>`:** O Grafo resolve a topologia via ordenação algorítmica e previne ciclos antes do processamento. O Motor (Engine) atua como a fachada principal (Facade), gerindo a taxa de amostragem (`sampleRate`), o tamanho do bloco (`blockSize`) e o despacho de execução temporal (`process_block()`).
*   **Lock-Free Logger:** O sistema possui um *Ring Buffer* de comunicação de produtor-único/consumidor-único (SPSC) nativo do C++. Permite a emissão segura de falhas (ex: macros `DSP2_LOG_ERROR`) a partir do loop crítico, que são consumidas assincronamente pelo Python.

## 3. Integração Híbrida Python-C++ (GRAPH_ROUTING.md)

A orquestração do pipeline é movida a dados (Data-Driven), separando a lógica de negócio do fluxo de execução.

*   **O Roteador Dinâmico (`GraphLoader`):** O módulo Python em `dsp2/graph_loader.py` analisa ficheiros JSON para construir a topologia. Ele lê a lista de `nodes`, instancia as classes C++ via `NodeFactory`, insere os parâmetros predefinidos (`parameters`) e solda as arestas virtuais (`edges`).
*   **Extração de Buffers:** O módulo expõe a função `get_node_output()` via Pybind11, permitindo que a camada Python espelhe e analise blocos do C++ em tempo real sem interrupção do Dataflow.

## 4. Catálogo de Nós Processadores (Fase 4.1 Concluída)

Os nós encontram-se em `nodes_cpp/` e são integralmente tipados (`template <typename T>`) para operar tanto em Simulação (`double`) como em Microcontroladores (`float`). Operam de forma **Híbrida**: a matemática combina valores base (via JSON) com modulação (via Dataflow).

*   **Nós Matemáticos Otimizados (`math_nodes.hpp`):**
    *   `Add`: Mixer de somatória ponto a ponto para fusão de caminhos.
    *   `Multiply`: Modulador em anel (Ring Modulator) ou Amplificador Controlado por Tensão (VCA).
    *   `Gain`: Escala linear de buffer de entrada.
    *   `Constant`: Gerador de Offset (corrente contínua).
*   **Nós Geradores (`oscillator_nodes.hpp`):**
    *   `SineOscillator`: Gerador base *stateful* que memoriza a sua fase entre blocos. Implementa a `DSP2FastMath::SineLUT` da Core API para evitar sobrecarga trigonométrica. Suporta simultaneamente Modulação de Frequência (FM) e Modulação de Fase (PM) alimentada por dados (Dataflow).

## 5. Ferramentas de Validação e Qualidade de Código

*   **DSP2 Test Harness (`dev_panel/signal_tester.py`):** Sistema robusto, escalável e acionado por linha de comando (CLI). O Harness lê qualquer grafo JSON arbitrário de complexidade ilimitada, aloca a memória e corre simulações concatenando $N$ blocos. No fim do ciclo, recolhe todos os dados e orquestra a visualização (plot) via `matplotlib`.
*   **Boas Práticas de C++ Moderno:** O código adere a um regime de "Zero Warnings". Parâmetros sem uso na interface (como o `sampleRate` em nós puros de matemática) têm o seu nome omitido; cast de variáveis de tamanho (ex: `static_cast<size_t>`) garantem comparações estritas entre índices e comprimentos de arrays.
*   **Dual Build Mode (CLAUDE.md):** Através do `CMakeLists.txt`, o alvo `SIMULATION` foca-se na prototipagem com Bindings Pybind11. O alvo `EMBEDDED` executa um "Corte Limpo", ignorando o Logger C++ (custo zero) e todo o código Python para compilação bruta da biblioteca (`libdsp2_core.a`).

## 6. Guia para IAs e Desenvolvedores (Próximos Passos)

**Como criar um novo nó:**
1. Crie a classe herdando de `NodeBase<T>` na diretoria `nodes_cpp/`.
2. Aloque a memória dos `output_buffers` apenas no `prepare()`.
3. Escreva a matemática vetorizada no `process()` (lembre-se de usar `const T* __restrict` para ler as entradas).
4. Registe o nó no `NodeFactory` dentro do ficheiro `core/engine.cpp` na função `register_core_nodes()`.
5. Crie um ficheiro de teste JSON e use o `signal_tester.py` para visualizar o resultado.

## 7. Padrões de Documentação de Código (Inline)

Para garantir que o motor permaneça limpo, rápido e compreensível, todos os novos ficheiros, classes e funções críticas **devem** ser documentados no código fonte. 

A documentação deve ser formatada usando o estilo **Doxygen**, o que permite a extração automática de manuais no futuro e garante que ferramentas como IntelliSense (VS Code/CLion) e Agentes LLM consigam ler o contrato de cada função.

### 7.1. Regras de Documentação para Nós C++

Sempre que criar um novo nó (ex: em `nodes_cpp/`), o cabeçalho da classe e os métodos principais devem ser anotados.

**O que documentar obrigatoriamente:**
1.  **A Classe:** O que o nó faz (o seu propósito matemático ou de processamento).
2.  **O Construtor:** Quais são as portas (Ports) de entrada (ex: Modulação de Frequência) e saída. Isto é crucial para que quem constrói o JSON saiba o que rotear para o `dest_port` e `source_port`.
3.  **O `set_parameter`:** Que parâmetros o nó aceita (ex: "frequency", "gain", "cutoff").
4.  **O `prepare` e `process`:** Documentar as proibições do `AGENTS.md` para lembrar os desenvolvedores de não alocarem memória no `process`.

### 7.2. Exemplo de Documentação Ideal (Template)

Aqui está um exemplo de como o código deve ser documentado usando comentários Doxygen (`/** ... */`):

```cpp
/**
 * @class LowPassFilter
 * @brief Aplica um filtro Passa-Baixa (Low-Pass) de um polo ao sinal de entrada.
 * 
 * Este nó demonstra a utilização de estado interno e memória (delay z-1) 
 * respeitando as regras de processamento em tempo real (Zero-Allocation).
 *
 * @note Entradas:
 *       - Porta 0: Sinal Principal
 *       - Porta 1: (Opcional) Modulação do Cutoff (CV)
 *       Saídas:
 *       - Porta 0: Sinal Filtrado
 */
template <typename T>
class LowPassFilter : public NodeBase<T> {
private:
    T cutoffFrequency = static_cast<T>(1000.0);
    T previousSample = static_cast<T>(0.0);

public:
    LowPassFilter() {
        this->input_buffers.resize(2, nullptr);
        this->output_buffers.resize(1, nullptr);
    }

    /**
     * @brief Modifica os parâmetros internos do nó.
     * @param param_name Nome do parâmetro (Suportado: "cutoff").
     * @param value Novo valor a ser aplicado.
     */
    void set_parameter(const std::string& param_name, double value) override {
        if (param_name == "cutoff") {
            cutoffFrequency = static_cast<T>(value);
        }
    }

    /**
     * @brief Prepara a memória e o estado do nó.
     * @warning Único local onde alocação dinâmica (new/malloc) é permitida.
     */
    void prepare(double /* sampleRate */, int blockSize) override {
        this->output_buffers[0] = new T[blockSize];
        previousSample = static_cast<T>(0.0); // Reset do estado
    }

    /**
     * @brief Executa o processamento matemático do bloco.
     * @warning NUNCA aloque memória ou use locks/IO dentro desta função!
     *          Utilize ponteiros __restrict para garantir a auto-vetorização (SIMD).
     */
    void process() override {
        // ... matemática do filtro ...
    }
    
    ~LowPassFilter() { delete[] this->output_buffers[0]; }
};
```

### 7.3. Documentação de API no Core

Se você modificar ou adicionar uma função matemática utilitária em `core/fast_math.hpp` ou `core/buffer_ops.hpp`, você **deve**:
1. Documentar a função inline com `@brief` e `@param`.
2. Atualizar imediatamente o ficheiro `/docs/api.md` com a nova função, descrevendo o seu impacto na performance (ex: se é otimizada para SIMD, se gasta muita RAM devido a uma *Lookup Table* muito grande, etc.).

## 8. Arquitetura Synchronous Dataflow (SDF) Multirate

O D(SP)^2 evoluiu de um modelo Single-Rate para uma arquitetura SDF Multirate robusta. 
O tamanho do bloco (`blockSize`) e a taxa de amostragem (`sampleRate`) não são mais impostos globalmente pelo motor, mas sim negociados topologicamente entre os vértices.

### 8.1. O Novo Ciclo de Vida do Nó (`NodeBase<T>`)
A assinatura de inicialização em `core/node_base.hpp` foi dividida em duas etapas para respeitar as regras de performance de tempo real descritas no `AGENTS.md`:
 
1.  `compute_dimensions()`: Executado após o motor injetar as dimensões dos nós de origem. O nó lê `input_block_sizes` e calcula `output_block_sizes` e `output_sample_rates`. (Exemplo: Um `Decimator` divide os valores de entrada pelo fator M).
2.  `prepare()`: Único local onde alocação dinâmica é permitida. O nó aloca seus arrays utilizando os tamanhos exatos calculados na fase anterior, poupando memória física.
 
### 8.2. Compilação Segura do Grafo (`Graph<T>::compile`)
Para evitar vazamentos de memória e *Buffer Overruns*, a função `compile()` agora inicializa todas as portas (conectadas ou não) com os valores base do motor. Em seguida, as dimensões são propagadas camada por camada seguindo a ordem topológica (Algoritmo de Kahn), garantindo que cada nó conheça o estado exato da sua vizinhança antes de instanciar o *Heap*.