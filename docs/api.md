# D(SP)^2 - Core DSP API Reference

Este documento lista as funções, utilitários matemáticos e classes base disponíveis no `core/` do D(SP)^2. 
**Nota para Agentes de IA:** Sempre consulte esta lista antes de implementar matemática customizada em um novo nó para reaproveitar código otimizado.

## 1. Operações de Buffer (SIMD Otimizadas)
Funções para manipular blocos inteiros de áudio de forma rápida.

Toda a matemática de blocos deve ser feita invocando o namespace `DSP2BufferOps`. Estas funções foram estruturadas para garantir o *auto-vectorizing* (SIMD) em -O3, trocando ciclos longos de processador por operações paralelas em hardware.

### `DSP2BufferOps::add<T>(T* __restrict dest, const T* __restrict src, int size)`
- **Descrição:** Realiza a soma de dois buffers ponto a ponto. O resultado é acumulado no buffer `dest`. Ideal para mixagem de sinais de áudio.

### `DSP2BufferOps::multiply<T>(T* __restrict dest, const T* __restrict src, int size)`
- **Descrição:** Multiplicação ponto a ponto (Modulação em Anel). 

### `DSP2BufferOps::multiply_scalar<T>(T* dest, T scalar, int size)`
- **Descrição:** Aplica um ganho/atenuação linear fixo a todo o bloco de áudio.

### `DSP2BufferOps::clear<T>(T* dest, int size)`
- **Descrição:** Preenche rapidamente o buffer especificado com zeros estáticos de acordo com a tipagem, sem chamar o memset global que pode ignorar otimizações de FPU.

## 2. Aproximações Matemáticas Rápidas (Fast Math)
Funções trigonométricas e logarítmicas que trocam precisão absoluta por velocidade extrema.

**Regra Estrita de Hardware:** Funções da biblioteca `<cmath>` são lentas em microcontroladores sem FPU ou causam gargalos de ciclos. Todo o cálculo matemático nos nós `nodes_cpp/` DEVE consumir as tabelas de pesquisa (Lookup Tables - LUTs) ou aproximações de Taylor listadas abaixo.

### `DSP2FastMath::SineLUT<T>`
- **Assinatura:** `inline T get_value(T phase_index) const`
- **Descrição:** Tabela de pesquisa pré-calculada para geração de senoide.
- **Configuração:** O tamanho padrão é definido pela constante `DSP2Config::SINE_LUT_DEFAULT_SIZE` em `core/constants.hpp`.
- **Notas de Performance:** Implementação $O(1)$ sem chamadas de `std::sin` no loop de áudio. Utiliza `DSP2Config::PI` (calculado via `std::acos(-1)`) para a geração inicial da tabela.

## 3. Sistema de Logging (Zero-Cost / Lock-Free)

Para enviar avisos ou capturar exceções matemáticas em tempo real para a interface Python sem causar gargalos na thread de áudio, utilize as macros do Core Logger. Elas usam um SPSC Ring Buffer sob o capô, garantindo segurança lock-free de O(1).

### Macros de Log:
* **`DSP2_LOG_INFO("Sua mensagem aqui");`**
* **`DSP2_LOG_ERROR("Sua mensagem aqui");`**

**Regras de Uso:**
- **Zero-Allocation:** As macros aceitam **APENAS** literais constantes de string (`const char*`). Nunca utilize formatação dinâmica (como `std::to_string()`) dentro delas para evitar a invocação do *heap*.
- **Otimização Embarcada:** O uso destas macros é totalmente seguro. Quando compilado com `DSP2_TARGET=EMBEDDED`, o compilador resolve estas chamadas para código vazio, resultando em custo zero de CPU e Memória para o microcontrolador.

## 4. Interface Python (Pybind11)

As funções abaixo estão disponíveis no módulo Python `dsp2._dsp2_core`.

### `get_logs() -> List[LogEvent]`
- **Descrição:** Ponto de entrada para o mecanismo de Polling do Python. Retorna todos os logs que foram emitidos pelo C++ desde a última chamada.
- **Uso Recomendado:** Chamar em um loop assíncrono ou thread de interface no Python para monitorar a saúde do motor sem interferir na thread de áudio.

### `Engine` (Binding)
- **Métodos:** `set_audio_parameters`, `prepare_engine`, `process_block`.
- **Tipo:** Instanciado em Python para rodar a simulação com precisão de 64-bits (`double`).

## 5. NodeFactory e Criação Dinâmica (Fase 3.3)
Para permitir que a interface Python (ou arquivos JSON) construa grafos de processamento sem necessidade de recompilar o motor, o $D(SP)^2$ utiliza um padrão Factory centralizado no arquivo `core/node_factory.hpp`.

**Regra Estrita para Agentes de IA:**
Sempre que você criar um novo arquivo de nó em `nodes_cpp/` (ex: `meu_filtro.hpp`), você **DEVE** registrá-lo na Factory. Caso contrário, o `GraphLoader` do Python retornará erro de "Tipo desconhecido" (ID -1).

### `NodeFactory<T>::get_instance().register_node()`
- **Assinatura:** `void register_node(const std::string& name, CreatorFunc creator)`
- **Uso:** Deve ser chamado na inicialização do sistema (dentro de `register_core_nodes()` no `engine.cpp`).
- **Exemplo de Registro:**
  ```cpp
  NodeFactory<double>::get_instance().register_node("FiltroBiquad", [](){ 
      return new FiltroBiquad<double>(); 
  });
  ```

## 6. Parâmetros em Array e Multirate (Novas APIs Fase 4.1)

Para suportar filtros avançados como Convolução (FIR) estrita no domínio do tempo, o D(SP)^2 agora suporta injeção de *Arrays* a partir do JSON diretamente para os nós C++.

### `NodeBase<T>::set_parameter_array` e `Engine<T>::set_node_parameter_array`
- **Assinatura:** `void set_parameter_array(const std::string& param_name, const std::vector<double>& values)`
- **Descrição:** Permite o envio de vetores inteiros (ex: Resposta ao Impulso de um Filtro) para inicialização no `prepare()`.
- **Uso Híbrido:** O `GraphLoader` (`dsp2/graph_loader.py`) inspeciona o JSON; se um parâmetro for uma lista Python, ele invoca esta nova API em vez do escalar `set_parameter`.

### Extração de Dimensões Físicas (Pybind11)
Para suportar a visualização física (Tempo em Segundos) em grafos Multirate, o módulo Python `dsp2._dsp2_core` expõe:
- `get_node_output_size(node_id, port) -> int`: Retorna o tamanho físico do bloco alocado por um nó específico. O método `get_node_output` agora utiliza esse valor dinamicamente para evitar leitura de memória lixo (*Buffer Overread*).
- `get_node_output_sample_rate(node_id, port) -> double`: Retorna a taxa de amostragem física (Fs) negociada para aquela porta.