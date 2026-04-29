## Plano de Desenvolvimento Integral do $D(SP)^2$
### Fase 1: O Coração do Sistema (Core C++ e Infraestrutura do Grafo)
* **1.1. Estrutura Base dos Vértices (`core/node_base.hpp`):** Criar a classe virtual pura base. A arquitetura deve permitir que os vértices (nós) sejam estendidos nativamente em C++ e também através de herança e polimorfismo no Python (permitindo lógica escrita em ambas as linguagens).
* **1.2. Motor e Grafo (`core/graph.cpp` e `core/engine.cpp`):** Desenvolver a lógica que liga os vértices, gerindo o fluxo de buffers e o ciclo iterativo.
* **1.3. Ajustes de Build:** Alterar o `CMakeLists.txt` para colocar o `.so` em `CMAKE_CURRENT_BINARY_DIR` e garantir a dependência do Python no `Dockerfile`.
### Fase 2: Matemática Rápida e Utilitários (Core C++)
* **2.1. Tabelas de Pesquisa (LUTs):** Criar osciladores tabulados em C++ para evitar a `<cmath>` pesada que bloqueia microcontroladores.
* **2.2. Fast Math e SIMD:** Implementar aproximações performantes em C++ para operações matriciais e de buffer que todos os vértices irão consumir.
* **2.3. Sistema de Logging Lock-Free:** Criar um Ring Buffer (SPSC) no core C++ para armazenar mensagens de erro sem alocação dinâmica. Implementar macros (`DSP2_LOG_ERROR`) que desativam o logger com custo zero quando compilado para o alvo `EMBEDDED`."

### Fase 3: A Ponte Pybind11 e Interface Híbrida
* **3.1. Bindings Avançados:** Expor a função de leitura do Ring Buffer do logger (`get_logs()`) para o Python através do `pybind11`.
* **3.2. Orquestração Híbrida:** Implementar uma thread ou mecanismo de polling assíncrono no `dsp2/build_graph.py` para consumir e exibir no terminal os avisos emitidos pelo core sem bloquear o fluxo de sinal.
* **3.3. Criação de Grafo Orientada a Dados:** Integrar um `NodeFactory`, permitindo a montagem de grafos complexos via arquivos **YAML/JSON** sem necessidade de alterar código ou recompilar.

### Fase 4: Implementação e Diversificação de Vértices (Módulos DSP)
* **4.1. Vértices de Alta Performance (`nodes_cpp/`):** Escrever os vértices pesados (Filtros Biquad, Reverbs, FFT) em C++ puro, respeitando as proibições de alocação dinâmica e RTTI.
* **4.2. Vértices de Prototipagem Rápida (`dsp2/nodes_py/`):** Desenvolver vértices em Python. Apesar de não serem tão performáticos quanto os de C++, são perfeitos para testar ideias de controlo, interfaces de IA e automações na simulação.
* **4.3. Sistema de Probes (Tap Points):** Implementar nós de interceptação baseados no sistema de Probes do AV-Scope. Permite copiar dados intermediários do sinal para visualização sem violar a imutabilidade dos buffers Zero-Copy.

### Fase 5: Ferramentas de Teste e Benchmarking
* **5.1. Painel de Desenvolvimento (`dev_panel/`):** Construir os scripts de validação como o `signal_tester.py` para inspecionar gráficos em `plots/` e ficheiros `.wav` nas saídas e Integrar a leitura de logs nos scripts de validação (como o signal_tester.py), exibindo métricas e alertas de erros matemáticos capturados pelo C++ durante as simulações..
* **5.2. Análise Híbrida (`run_benchmark.py`):** Medir o impacto temporal e a assimetria entre chamar a função `process()` num vértice C++ versus num vértice sobrecarregado no Python.
* **5.3. Simulador de Fluxo de Arquivos (Dual Mode):** Adaptar a lógica de *File Throttling* (`FilePlaybackStream`) do AV-Scope, permitindo que arquivos de áudio (.wav) sejam processados pelo motor C++ mimetizando o tempo real de hardware cadenciado.
* **5.4. Visualização PyQtGraph:** Integrar os widgets `ScopeGraph`, layouts de auto-grade e detectores do AV-Scope para monitoramento visual acelerado por GPU no painel de desenvolvimento.

### Fase 6: Homologação para Embarcados (Corte Limpo)
* **6.1. Compilação do Núcleo Rigoroso:** Configurar a submissão com `DSP2_TARGET=EMBEDDED`. Isto assegura que todos os vértices escritos em Python são ignorados e apenas a matemática rigorosa de `nodes_cpp/` segue para o microcontrolador.
* **6.2. Documentação e Exemplos Finais (`examples/`):** Integrar e apresentar os vértices C++ embarcados a interagir com rotinas de I/O de microcontroladores reais.

### Registo de Qualidade e Testes (QA)
- **Fase 1 Validada:** O teste de integração `tests/test_phase1.cpp` foi criado para validar a arquitetura Zero-Copy e a Ordenação Topológica. 
- **Boas Práticas de Teste:** O projeto utiliza o `CTest` do CMake. Para rodar a suite de testes atualizada sem afetar a simulação ou código embarcado, os programadores devem rodar `make test` dentro da pasta de `build-embedded`.
- **Nós de Teste (Dummies):** Sempre que precisar testar o fluxo de sinal sem invocar matemática complexa da Fase 4, utilize ou expanda o `DummyGenerator` e `DummyMultiplier` implementados nos testes.