# $D(SP)^2$ - Agent Instructions & System Prompt

Você está auxiliando no desenvolvimento do **$D(SP)^2$ (Digital Signal Processing Simulation Program)**, um software de processamento de sinais baseado em fluxo de dados (dataflow), escrito com um core em C++ e interface/bindings em Python.

Sempre que você for criar, modificar ou analisar um nó (node) de processamento, você deve seguir RIGOROSAMENTE as regras abaixo.

## 1. Arquitetura do Sistema (Dataflow)
O D(SP)^2 funciona através de um grafo direcionado onde cada "nó" representa uma operação matemática ou de DSP. 

* **Estrutura do Nó:** Todo novo nó C++ deve herdar da classe base `[NOME_DA_CLASSE_BASE]` e implementar obrigatoriamente a função de processamento `[NOME_DA_FUNCAO_DE_PROCESSAMENTO]`.
* **Entradas e Saídas:** Os nós se comunicam passando buffers de áudio/sinais de tamanho fixo. As entradas devem ser declaradas no construtor do nó. 
* **Ausência de Estado Global:** Os nós devem ser autocontidos. Não utilize variáveis globais para armazenar estados (como delays ou fases de osciladores); todo o estado interno deve pertencer à instância da classe do nó.
* **Imutabilidade:** É estritamente proibido que um nó modifique os dados do seu buffer de entrada. A passagem de sinal entre arestas é feita por referência de memória (Zero-Copy). Para garantir isto, as variáveis de entrada na classe base (node_base.hpp) e nos nós herdeiros devem ser sempre declaradas como ponteiros constantes: const T* input_buffer. Qualquer tentativa de reescrever input_buffer[i] = ... resultará num erro de compilação. Os nós apenas podem escrever nos seus próprios T* output_buffer.

## 2. Restrições de Performance e Sistema Embarcado
Como este é um motor de processamento de sinais de áudio/tempo real, a performance e o determinismo são críticos. Dentro do loop de processamento de áudio (a função que processa os buffers amostra por amostra):

* **PROIBIDO Alocação Dinâmica de Memória:** Nunca use `new`, `malloc`, ou instancie novos `std::vector` ou arrays estáticos dentro do loop de processamento. Toda a alocação de memória (buffers, janelas de FFT, arrays de delay) DEVE ser feita durante a inicialização (no construtor ou no método `prepare()`).
* **Operações Pesadas:** Evite chamadas de sistema, I/O de disco (printf/std::cout), ou locks de mutex bloqueantes dentro do bloco de processamento.
* **Vetorização:** Sempre que possível, estruture os loops matemáticos de forma que o compilador consiga aplicar otimizações de SIMD (vetorização).
* **PROIBIDO Exceções e RTTI:** O alvo `EMBEDDED` é compilado com `-fno-exceptions` e `-fno-rtti`. O uso de `try/catch` ou `dynamic_cast` está estritamente proibido em todo o repositório C++. Em caso de falha de validação, retorne códigos de erro (enums) ou utilize retornos vazios.
* **PROIBIDO Biblioteca Matemática Padrão:** Não utilize funções da `<cmath>` (ex: `std::sin`, `std::exp`, `std::log`) dentro do loop de áudio. Utilize apenas as funções de "Fast Math" e Lookup Tables (LUTs) fornecidas na API do Core.
* **Tipagem Genérica (Templates):** Todo nó deve ser escrito como `template <typename T>` para suportar processamento em `double` (Simulação/Python) e `float` (Hardware/Microcontrolador).
* **Modo Mínimo (Macros de Profiling):** Qualquer código destinado a medir tempo de execução, uso de memória ou debug para enviar ao Python deve ser encapsulado num bloco `#ifndef DSP2_EMBEDDED_MODE`.

## 3. Manutenção de Documentação
O diretório `core/` contém o motor de tempo real do sistema. Para que IAs e outros desenvolvedores não criem funções matemáticas redundantes nos nós, mantemos um registro rigoroso no arquivo `docs/api.md`.

* **REGRA DE ATUALIZAÇÃO OBRIGATÓRIA:** Se você (o Agente) modificar, adicionar ou otimizar qualquer utilitário matemático, de buffer ou de hardware dentro da pasta `core/` (ex: criar uma nova aproximação de logaritmo rápida, um novo filtro em C++ base, ou um utilitário SIMD), você **DEVE** imediatamente atualizar o arquivo `docs/api.md` para refletir essa adição.
* **Formato:** Siga o padrão já estabelecido no `docs/api.md`, incluindo nome, assinatura, descrição e notas de performance (especialmente sobre uso de memória e otimizações vetoriais).
* **Reuso:** Antes de escrever matemática complexa do zero dentro de um arquivo em `nodes_cpp/`, leia o `docs/api.md` para verificar se a função já existe no core.

## 4. Criação de Novos Nós
A consistência da arquitetura é fundamental para que o motor em C++ funcione sem falhas e para que a interface em Python consiga mapear os módulos corretamente.

* **USO OBRIGATÓRIO DE TEMPLATES:** Sempre que for solicitado a você (o Agente) a criação de um novo nó de processamento (seja um oscilador, filtro, envelope ou controlador físico), você **NÃO DEVE** inventar uma estrutura de classe do zero.
* Você deve **obrigatoriamente ler o arquivo `docs/node-template.md`** e usar a exata estrutura de código fornecida lá.
* Preste atenção especial à separação entre a função `prepare()` (onde a alocação de memória é permitida) e a função `process()` (onde a alocação de memória é estritamente proibida).

## 5. Ambiente de Desenvolvimento (Docker)
O projeto é conteinerizado para garantir a reprodutibilidade da compilação do C++ e das dependências do Python.
* **Execução:** Não compile o código diretamente na máquina host. Sempre utilize o ambiente Docker configurado no `docker-compose.yml`.
* **Hardware:** O acesso ao hardware é mapeado pelo Docker via diretiva `devices`. Se um novo hardware for adicionado, instrua o usuário a atualizar o `docker-compose.yml`.

## 6. Sistema de Logging e Debug (Tempo Real)
A depuração entre a ponte C++ e Python não deve comprometer a performance do motor de áudio. Se precisar criar logs ou rastrear erros matemáticos dentro da função `process()` de um nó, **NÃO USE** `std::cout`, `printf` ou ferramentas padrão. Você deve utilizar o Logger Nativo do Core.
Ao trabalhar com o sistema de *logs* do $D(SP)^2$, siga RIGOROSAMENTE estas 4 regras:
### 1. Custo Zero no Modo Embarcado (Macro de Exclusão)
O logger só pode existir quando o sistema compila para `SIMULATION`. Todo e qualquer comando de log deve estar encapsulado em macros que o compilador ignore completamente no alvo `EMBEDDED`.
* **Uso Obrigatório:** Utilize apenas as macros fornecidas (ex: `DSP2_LOG_INFO()`, `DSP2_LOG_ERROR()`), que internamente estão protegidas por `#ifndef DSP2_EMBEDDED_MODE`.
### 2. Lock-Free e Zero-I/O (Segurança de Tempo Real)
* **PROIBIDO I/O:** Nunca imprima no terminal a partir de um nó em C++.
* **Mecanismo:** O logger atua como um **Ring Buffer SPSC (Single-Producer, Single-Consumer)**. O nó (Produtor) apenas copia a mensagem de erro para o buffer pré-alocado e avança o ponteiro de forma atómica. É proibida a utilização de *mutexes* (locks) neste processo de escrita.
### 3. Zero Alocação Dinâmica de Strings
* **PROIBIDO Concatenar ou Alocar Strings:** Não instancie ou modifique `std::string` dinamicamente no momento do *log* (ex: evitar `DSP2_LOG_ERROR("Erro: " + std::to_string(val))`), pois isso invoca alocação no *heap*.
* Utilize apenas mensagens literais constantes (`const char*`) ou *buffers* de tamanho fixo previamente alocados na fase `prepare()`.
### 4. Orquestração e Consumo via Python
* As mensagens armazenadas no Ring Buffer em C++ devem ser consumidas exclusivamente pelo ambiente Python.
* A ponte `pybind11` (`bindings/bind_python.cpp`) deve expor uma função de *polling* (ex: `dsp2_core.get_logs()`) para que o terminal Python possa ler as falhas atiradas pelos nós sem interromper a execução do DSP.
**Exemplo de Implementação Correta no `process()`:**
```cpp
void process() override {
    if (divisor == 0.0f) {
        // Correto: Usa a macro segura, string estática, O(1), sem locks.
        DSP2_LOG_ERROR("Divisão por zero detectada no módulo Biquad.");
        return; 
    }
    // ... matemática continua
}
```

## 7. Árvore de arquivos

O projeto deve conter os seguintes arquivos nessa estrutura.

```bash
DSP2/
├── CMakeLists.txt         
├── pyproject.toml         
├── AGENTS.md              
├── CLAUDE.md 
├── Dockerfile     
├── docker-compose.yml        
├── .dockerignore
├── .gitignore
├── .cursorrules
├── LICENSE
├── README.md
│
├── core/                  
│   ├── graph.cpp          
│   ├── engine.cpp         
│   └── node_base.hpp        
│
├── bindings/              
│   └── bind_python.cpp      
│
├── dsp2/                  
│   ├── __init__.py        
│   ├── build_graph.py     
│   └── nodes_py/    
│
├── nodes_cpp/             
│
├── examples/              
│
├── docs/
│
└── dev_panel/             
    ├── run_benchmark.py   
    └── signal_tester.py  
```
