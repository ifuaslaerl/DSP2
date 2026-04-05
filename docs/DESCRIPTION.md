PROJETO: $D(SP)^2$ - Digital Signal Processing Simulation Program
EQUIPE: Luís, Caio e Rodrigo

## DESCRIÇÃO DO PROJETO

O D(SP)^2 é uma ferramenta de prototipagem e simulação voltada para o 
Processamento Digital de Sinais. Ele opera sob o paradigma de programação 
baseada em fluxo de dados. 

O objetivo principal é permitir que os usuários construam e simulem sistemas de 
processamento de sinais conectando blocos modulares independentes em um grafo 
direcionado. A ferramenta abstrai a complexidade do código de baixo nível, 
focando na interconexão de sinais e na validação de modelos matemáticos.

## ARQUITETURA DO SISTEMA
Para garantir escalabilidade e facilitar o trabalho em equipe, a arquitetura 
é modular, separando estritamente a interface visual do motor matemático. Ela 
é dividida nos componentes principais abaixo:

### MOTOR DE FLUXO DE DADOS
É responsável por:
- Mapear a topologia do grafo para determinar a ordem 
  correta de execução dos blocos.
- Gerenciar loops de realimentação: identificar ciclos no grafo 
  e garantir que a dependência circular não cause deadlocks na execução.
- Orquestrar o agendamento de execução.
- Propagar as amostras de sinal garantindo que um bloco só execute quando tiver 
  dados suficientes em suas entradas.

### BIBLIOTECA DE BLOCOS
Módulos isolados que executam as operações matemáticas. Dividem-se em:
- Fontes: Geradores de sinal.
- Sumidouros: Terminações de sinal.
- Processadores: Filtros, transformadas, moduladores, operadores matemáticos.

### SISTEMA DE BUFFERS E PORTAS
Estruturas de dados que implementam as arestas do grafo. 
Elas conectam a porta de saída de um bloco à porta de entrada do bloco seguinte,
gerenciando o armazenamento temporário de amostras no fluxo.
