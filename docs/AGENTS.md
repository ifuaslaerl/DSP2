# $D(SP)^2$ - Agent Instructions & System Prompt

Você está auxiliando no desenvolvimento do **$D(SP)^2$ (Digital Signal Processing Simulation Program)**, um software de processamento de sinais baseado em fluxo de dados (dataflow), escrito com um core em C++ e interface/bindings em Python.

Sempre que você for criar, modificar ou analisar um nó (node) de processamento, você deve seguir RIGOROSAMENTE as regras abaixo.

## 1. Arquitetura do Sistema (Dataflow)
O D(SP)^2 funciona através de um grafo direcionado onde cada "nó" representa uma operação matemática ou de DSP. 

* **Estrutura do Nó:** Todo novo nó C++ deve herdar da classe base `[NOME_DA_CLASSE_BASE]` e implementar obrigatoriamente a função de processamento `[NOME_DA_FUNCAO_DE_PROCESSAMENTO]`.
* **Entradas e Saídas:** Os nós se comunicam passando buffers de áudio/sinais de tamanho fixo. As entradas devem ser declaradas no construtor do nó. 
* **Ausência de Estado Global:** Os nós devem ser autocontidos. Não utilize variáveis globais para armazenar estados (como delays ou fases de osciladores); todo o estado interno deve pertencer à instância da classe do nó.

## 2. Restrições de Performance (Tempo Real)
Como este é um motor de processamento de sinais de áudio/tempo real, a performance e o determinismo são críticos. Dentro do loop de processamento de áudio (a função que processa os buffers amostra por amostra):

* **PROIBIDO Alocação Dinâmica de Memória:** Nunca use `new`, `malloc`, ou instancie novos `std::vector` ou arrays estáticos dentro do loop de processamento. Toda a alocação de memória (buffers, janelas de FFT, arrays de delay) DEVE ser feita durante a inicialização (no construtor ou no método `prepare()`).
* **Operações Pesadas:** Evite chamadas de sistema, I/O de disco (printf/std::cout), ou locks de mutex bloqueantes dentro do bloco de processamento.
* **Vetorização:** Sempre que possível, estruture os loops matemáticos de forma que o compilador consiga aplicar otimizações de SIMD (vetorização).

## 3. Manutenção de Documentação (Core API)
O diretório `core/` contém o motor de tempo real do sistema. Para que IAs e outros desenvolvedores não criem funções matemáticas redundantes nos nós, mantemos um registro rigoroso no arquivo `docs/dsp-api.md`.

* **REGRA DE ATUALIZAÇÃO OBRIGATÓRIA:** Se você (o Agente) modificar, adicionar ou otimizar qualquer utilitário matemático, de buffer ou de hardware dentro da pasta `core/` (ex: criar uma nova aproximação de logaritmo rápida, um novo filtro em C++ base, ou um utilitário SIMD), você **DEVE** imediatamente atualizar o arquivo `docs/dsp-api.md` para refletir essa adição.
* **Formato:** Siga o padrão já estabelecido no `docs/dsp-api.md`, incluindo nome, assinatura, descrição e notas de performance (especialmente sobre uso de memória e otimizações vetoriais).
* **Reuso:** Antes de escrever matemática complexa do zero dentro de um arquivo em `nodes_cpp/`, leia o `docs/dsp-api.md` para verificar se a função já existe no core.

## 4. Criação de Novos Nós (Templates)
A consistência da arquitetura é fundamental para que o motor em C++ funcione sem falhas e para que a interface em Python consiga mapear os módulos corretamente.

* **USO OBRIGATÓRIO DE TEMPLATES:** Sempre que for solicitado a você (o Agente) a criação de um novo nó de processamento (seja um oscilador, filtro, envelope ou controlador físico), você **NÃO DEVE** inventar uma estrutura de classe do zero.
* Você deve **obrigatoriamente ler o arquivo `docs/cpp-node-template.md`** (para nós em C++) ou `docs/py-node-template.md` (para protótipos em Python) e usar a exata estrutura de código fornecida lá.
* Preste atenção especial à separação entre a função `prepare()` (onde a alocação de memória é permitida) e a função `process()` (onde a alocação de memória é estritamente proibida).

## 5. Ambiente de Desenvolvimento (Docker)
O projeto é conteinerizado para garantir a reprodutibilidade da compilação do C++ e das dependências do Python.
* **Execução:** Não compile o código diretamente na máquina host. Sempre utilize o ambiente Docker configurado no `docker-compose.yml`.
* **Hardware:** O acesso ao hardware é mapeado pelo Docker via diretiva `devices`. Se um novo hardware for adicionado, instrua o usuário a atualizar o `docker-compose.yml`.

## 6. Árvore de arquivos

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
