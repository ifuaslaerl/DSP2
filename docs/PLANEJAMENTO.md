## Plano de Desenvolvimento Integral do $D(SP)^2$
### Fase 1: O Coração do Sistema (Core C++ e Infraestrutura do Grafo)
* **1.1. Estrutura Base dos Vértices (`core/node_base.hpp`):** Criar a classe virtual pura base. A arquitetura deve permitir que os vértices (nós) sejam estendidos nativamente em C++ e também através de herança e polimorfismo no Python (permitindo lógica escrita em ambas as linguagens).
* **1.2. Motor e Grafo (`core/graph.cpp` e `core/engine.cpp`):** Desenvolver a lógica que liga os vértices, gerindo o fluxo de buffers e o ciclo iterativo.
* **1.3. Ajustes de Build:** Alterar o `CMakeLists.txt` para colocar o `.so` em `CMAKE_CURRENT_BINARY_DIR` e garantir a dependência do Python no `Dockerfile`.
### Fase 2: Matemática Rápida e Utilitários (Core C++)
* **2.1. Tabelas de Pesquisa (LUTs):** Criar osciladores tabulados em C++ para evitar a `<cmath>` pesada que bloqueia microcontroladores.
* **2.2. Fast Math e SIMD:** Implementar aproximações performantes em C++ para operações matriciais e de buffer que todos os vértices irão consumir.
### Fase 3: A Ponte Pybind11 e Interface Híbrida
* **3.1. Bindings Avançados (`bindings/bind_python.cpp`):** Expor a classe C++ para o Python. Será crucial usar trampoline classes no `pybind11` para permitir que utilizadores definam novos vértices puramente no lado Python, fazendo o motor em C++ chamar o código Python durante as simulações.
* **3.2. Orquestração Híbrida (`dsp2/build_graph.py`):** Criar a fundação que permite ligar vértices C++ e Python no mesmo grafo de áudio.
### Fase 4: Implementação e Diversificação de Vértices (Módulos DSP)
* **4.1. Vértices de Alta Performance (`nodes_cpp/`):** Escrever os vértices pesados (Filtros Biquad, Reverbs, FFT) em C++ puro, respeitando as proibições de alocação dinâmica e RTTI.
* **4.2. Vértices de Prototipagem Rápida (`dsp2/nodes_py/`):** Desenvolver vértices em Python. Apesar de não serem tão performáticos quanto os de C++, são perfeitos para testar ideias de controlo, interfaces de IA e automações na simulação.
### Fase 5: Ferramentas de Teste e Benchmarking
* **5.1. Painel de Desenvolvimento (`dev_panel/`):** Construir os scripts de validação como o `signal_tester.py` para inspecionar gráficos em `plots/` e ficheiros `.wav` nas saídas.
* **5.2. Análise Híbrida (`run_benchmark.py`):** Medir o impacto temporal e a assimetria entre chamar a função `process()` num vértice C++ versus num vértice sobrecarregado no Python.
### Fase 6: Homologação para Embarcados (Corte Limpo)
* **6.1. Compilação do Núcleo Rigoroso:** Configurar a submissão com `DSP2_TARGET=EMBEDDED`. Isto assegura que todos os vértices escritos em Python são ignorados e apenas a matemática rigorosa de `nodes_cpp/` segue para o microcontrolador.
* **6.2. Documentação e Exemplos Finais (`examples/`):** Integrar e apresentar os vértices C++ embarcados a interagir com rotinas de I/O de microcontroladores reais.