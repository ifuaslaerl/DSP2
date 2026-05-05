# D(SP)^2 - Core DSP API Reference

Este documento lista as funções, utilitários matemáticos e classes base disponíveis no `core/` do D(SP)^2. 
**Nota para Agentes de IA:** Sempre consulte esta lista antes de implementar matemática customizada em um novo nó para reaproveitar código otimizado.

## 1. Operações de Buffer (SIMD Otimizadas)
Funções para manipular blocos inteiros de forma rápida.

Toda a matemática de blocos deve ser feita invocando o namespace `DSP2BufferOps`. Estas funções foram estruturadas para garantir o *auto-vectorizing* (SIMD) em -O3, trocando ciclos longos de processador por operações paralelas em hardware.

### `DSP2BufferOps::add<T>(T* __restrict dest, const T* __restrict src, int size)`
- **Descrição:** Realiza a soma de dois buffers ponto a ponto. O resultado é acumulado no buffer `dest`. Ideal para mixagem de sinais.

### `DSP2BufferOps::multiply<T>(T* __restrict dest, const T* __restrict src, int size)`
- **Descrição:** Multiplicação ponto a ponto (Modulação em Anel). 

### `DSP2BufferOps::multiply_scalar<T>(T* dest, T scalar, int size)`
- **Descrição:** Aplica um ganho/atenuação linear fixo a todo o bloco.

### `DSP2BufferOps::clear<T>(T* dest, int size)`
- **Descrição:** Preenche rapidamente o buffer especificado com zeros estáticos de acordo com a tipagem, sem chamar o memset global que pode ignorar otimizações de FPU.

## 2. Aproximações Matemáticas Rápidas (Fast Math)
Funções trigonométricas e logarítmicas que trocam precisão absoluta por velocidade extrema.

**Regra Estrita de Hardware:** Funções da biblioteca `<cmath>` são lentas em microcontroladores sem FPU ou causam gargalos de ciclos. Todo o cálculo matemático nos nós `nodes_cpp/` DEVE consumir as tabelas de pesquisa (Lookup Tables - LUTs) ou aproximações de Taylor listadas abaixo.

### `DSP2FastMath::SineLUT<T>`
- **Assinatura:** `inline T get_value(T phase_index) const`
- **Descrição:** Tabela de pesquisa pré-calculada para geração de senoide.
- **Configuração:** O tamanho padrão é definido pela constante `DSP2Config::SINE_LUT_DEFAULT_SIZE` em `core/constants.hpp`.
- **Notas de Performance:** Implementação $O(1)$ sem chamadas de `std::sin` no loop. Utiliza `DSP2Config::PI` (calculado via `std::acos(-1)`) para a geração inicial da tabela.

### `DSP2FastMath::FrequencyToMidiNoteLUT<T>`
- **Assinatura:** `inline T get_note(T frequency) const`
- **Descrição:** Converte frequência em Hz para a nota MIDI inteira mais próxima usando A4 = 440 Hz e MIDI 69.
- **Configuração:** As fronteiras entre semitons são pré-calculadas na construção do objeto, fora do ciclo crítico.
- **Notas de Performance:** O lookup em `process()` não chama `<cmath>`, não aloca memória e usa apenas comparações lineares contra 127 fronteiras fixas. Frequências `<= 0` retornam `0`; valores acima da faixa MIDI retornam `127`.

## 3. FFT e Análise Espectral

Utilitários para transformar blocos de áudio real em espectros de frequência. Devem ser usados por nós de análise em vez de cada nó implementar uma FFT própria.

### `DSP2FFT::is_power_of_two(int value) -> bool`
- **Descrição:** Retorna se o tamanho informado é uma potência de 2 válida para a FFT radix-2.
- **Notas de Performance:** Função inline, $O(1)$, sem alocação.

### `DSP2FFT::next_power_of_two(int value) -> int`
- **Descrição:** Retorna a menor potência de 2 maior ou igual ao valor informado.
- **Notas de Performance:** Função inline, usada em fase de negociação/preparação de dimensões.

### `DSP2FFT::RealFFTPlan<T>`
- **Assinaturas principais:** `bool configure(int requested_size)`, `bool execute(const T* input, int input_size)`, `T real(int bin) const`, `T imag(int bin) const`.
- **Descrição:** Plano FFT radix-2 para entrada real. `configure()` aloca buffers internos, tabela de bit-reversal e twiddles; `execute()` copia a entrada para workspace pré-alocado, aplica zero-padding quando necessário e executa a FFT.
- **Notas de Performance:** `execute()` não faz alocação dinâmica, não usa I/O e não chama funções trigonométricas. A geração de twiddles com `<cmath>` ocorre apenas em `configure()`, fora do loop crítico.

### Nó `SpectrumAnalyser`
- **Tipo de Factory:** `"SpectrumAnalyser"` e alias `"SpectrumAnalyzer"`.
- **Entradas:** Porta 0 recebe áudio real no domínio do tempo, preferencialmente já passado pelo nó `Windowing`.
- **Saídas:** Porta 0 emite potência espectral por bin; porta 1 emite a frequência em Hz correspondente a cada bin.
- **Parâmetros:** `fft_size` opcional. Se ausente ou menor que o bloco de entrada, o nó usa o próximo power-of-two maior ou igual ao bloco de entrada. Se maior que o bloco, aplica zero-padding.
- **Formato:** Espectro one-sided com `fft_size / 2 + 1` bins, de DC até Nyquist.
- **Notas de Performance:** A saída usa potência (`real² + imag²`) normalizada por `fft_size²`, evitando `std::sqrt` dentro de `process()`.

### Nó `SpectralPeakPicker`
- **Tipo de Factory:** `"SpectralPeakPicker"`.
- **Entradas:** Porta 0 recebe potência por bin; porta 1 recebe frequência em Hz por bin. Uso esperado após `SpectrumAnalyser`.
- **Saídas:** Porta 0 emite as frequências selecionadas em Hz; porta 1 emite as potências correspondentes.
- **Parâmetros:** `peak_count` (default `6`), `min_frequency` (default `20.0`), `max_frequency` (default `0`, sem limite), `threshold` (default `0.0`) e `min_bin_distance` (default `1`).
- **Critério de Pico:** Um candidato deve estar dentro da faixa de frequência, acima do threshold e ser máximo local (`power[i] > power[i - 1]` e `power[i] > power[i + 1]`). Os candidatos são retornados em ordem decrescente de potência.
- **Formato:** As saídas têm tamanho fixo `peak_count`. Quando há menos picos disponíveis, o restante é preenchido com zero.
- **Notas de Performance:** A seleção usa buffers internos pré-alocados e inserção ordenada top-N, sem `std::sort`, alocação dinâmica ou I/O dentro de `process()`.
- **Exemplo de Grafo:** `AudioFileInput -> Windowing -> SpectrumAnalyser -> SpectralPeakPicker`.

### Nó `FrequencyToMidiNote`
- **Tipo de Factory:** `"FrequencyToMidiNote"`.
- **Entradas:** Porta 0 recebe frequências em Hz, tipicamente a saída de frequências do `SpectralPeakPicker`.
- **Saídas:** Porta 0 emite a nota MIDI inteira mais próxima em formato numérico `T`.
- **Formato:** O tamanho e a taxa de amostragem da saída seguem a entrada. Frequências `<= 0` emitem `0`, preservando o padding por zero do `SpectralPeakPicker`; notas acima da faixa MIDI são limitadas a `127`.
- **Notas de Performance:** Usa `DSP2FastMath::FrequencyToMidiNoteLUT<T>`; não há alocação dinâmica, I/O ou chamadas de `<cmath>` dentro de `process()`.
- **Exemplo de Grafo:** `AudioFileInput -> Windowing -> SpectrumAnalyser -> SpectralPeakPicker -> FrequencyToMidiNote`.

## 4. Sistema de Logging (Zero-Cost / Lock-Free)

Para enviar avisos ou capturar exceções matemáticas em tempo real para a interface Python sem causar gargalos na thread, utilize as macros do Core Logger. Elas usam um SPSC Ring Buffer sob o capô, garantindo segurança lock-free de O(1).

### Macros de Log:
* **`DSP2_LOG_INFO("Sua mensagem aqui");`**
* **`DSP2_LOG_ERROR("Sua mensagem aqui");`**

**Regras de Uso:**
- **Zero-Allocation:** As macros aceitam **APENAS** literais constantes de string (`const char*`). Nunca utilize formatação dinâmica (como `std::to_string()`) dentro delas para evitar a invocação do *heap*.
- **Otimização Embarcada:** O uso destas macros é totalmente seguro. Quando compilado com `DSP2_TARGET=EMBEDDED`, o compilador resolve estas chamadas para código vazio, resultando em custo zero de CPU e Memória para o microcontrolador.

## 5. Interface Python (Pybind11)

As funções abaixo estão disponíveis no módulo Python `dsp2._dsp2_core`.

### `get_logs() -> List[LogEvent]`
- **Descrição:** Ponto de entrada para o mecanismo de Polling do Python. Retorna todos os logs que foram emitidos pelo C++ desde a última chamada.
- **Uso Recomendado:** Chamar em um loop assíncrono ou thread de interface no Python para monitorar a saúde do motor sem interferir na thread principal.

### `Engine` (Binding)
- **Métodos:** `set_signal_parameters`, `prepare_engine`, `process_block`.
- **Tipo:** Instanciado em Python para rodar a simulação com precisão de 64-bits (`double`).

## 6. NodeFactory e Criação Dinâmica (Fase 3.3)
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

## 7. Parâmetros em Array e Multirate (Novas APIs Fase 4.1)

Para suportar filtros avançados como Convolução (FIR) estrita no domínio do tempo, o D(SP)^2 agora suporta injeção de *Arrays* a partir do JSON diretamente para os nós C++.

### `NodeBase<T>::set_parameter_array` e `Engine<T>::set_node_parameter_array`
- **Assinatura:** `void set_parameter_array(const std::string& param_name, const std::vector<double>& values)`
- **Descrição:** Permite o envio de vetores inteiros (ex: Resposta ao Impulso de um Filtro) para inicialização no `prepare()`.
- **Uso Híbrido:** O `GraphLoader` (`dsp2/graph_loader.py`) inspeciona o JSON; se um parâmetro for uma lista Python, ele invoca esta nova API em vez do escalar `set_parameter`.

### Extração de Dimensões Físicas (Pybind11)
Para suportar a visualização física (Tempo em Segundos) em grafos Multirate, o módulo Python `dsp2._dsp2_core` expõe:
- `get_node_output_size(node_id, port) -> int`: Retorna o tamanho físico do bloco alocado por um nó específico. O método `get_node_output` agora utiliza esse valor dinamicamente para evitar leitura de memória lixo (*Buffer Overread*).
- `get_node_output_sample_rate(node_id, port) -> double`: Retorna a taxa de amostragem física (Fs) negociada para aquela porta.
- `get_node_output_port_count(node_id) -> int`: Retorna a quantidade de portas de saída declaradas por um nó. Uso recomendado para ferramentas de inspeção em Python que precisam capturar todas as saídas sem assumir que todo nó possui apenas a porta `0`.
  - **Notas de Performance:** API de introspecção para fase de simulação/diagnóstico. A consulta é $O(1)$ e não participa do ciclo crítico de processamento.
