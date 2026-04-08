# $D(SP)^2$

## Digital Signal Processing Simulation Program

$D(SP)^2$ É uma ferramenta feita para auxiliar a prototipagem de sistemas de processamento digital de sinais, com arquitetura modular, escalável e suporte nativo para embarcar a modelagem.

## **Pré-Requisitos**

* **Docker** e **Docker Compose** instalados na máquina host.
  * *Nota de versão:* Recomendamos a utilização do Docker Compose V2.
* Sistema operacional Linux

## **Instalação**

```bash
# 1. Clone este repositório para a sua máquina local.
git clone https://github.com/ifuaslaerl/DSP2.git

# 2. Inicie o ambiente isolado em segundo plano.
sudo docker-compose up -d --build
```

## **Compilação**

O nosso sistema de compilação utiliza o CMake e está dividido em dois alvos principais: a simulação com *bindings* em Python e a biblioteca estática em C++ para sistemas embarcados. 

**⚠️ Regra de Ouro:** Nunca compiles o código diretamente na raiz do projeto. Cria sempre uma pasta de *build* separada. O nosso ficheiro `.gitignore` já está configurado para ignorar qualquer diretório que comece por `build-` ou `build/`. Isto garante que cada membro da equipa possa compilar o código localmente sem enviar ficheiros binários ou temporários para o repositório.

### Compilar para Simulação
Este é o modo predefinido. Ele compila a matemática do *core* e gera a biblioteca partilhada (`.so`) através do `pybind11`, permitindo que o Python construa o grafo e orquestre o motor.

Dentro do terminal do Docker (após executar `sudo docker-compose exec dsp2-env /bin/bash`), executa os seguintes comandos:

```bash
# Criar e entrar na pasta de build da simulação
mkdir build-sim
cd build-sim

# Configurar o CMake apontando para o diretório raiz (..)
cmake -DDSP2_TARGET=SIMULATION ..

# Executar a compilação
make
```

## Compilar para Sistema Embarcado 

Este modo isola o C++ de qualquer dependência do Sistema Operativo ou do Python. Ele ignora a pasta bindings/ e gera apenas a biblioteca estática (libdsp2_core.a) que será posteriormente incluída no firmware do microcontrolador.

Dentro do terminal do Docker, execute:

```bash
# 1. Voltar à raiz (se estiveres noutra pasta de build) e criar uma nova pasta
mkdir build-embedded
cd build-embedded

# 2. Configurar o CMake especificando o alvo EMBEDDED
cmake -DDSP2_TARGET=EMBEDDED ..

# 3. Executar a compilação
make
```

## **Modo de Uso**

Todo o desenvolvimento, a compilação do motor em C++ e a execução da interface em Python devem ser feitos exclusivamente dentro do contêiner para garantir a reprodutibilidade do sistema em tempo real.

```bash
# Para entrar no terminal interativo do Docker
sudo docker-compose exec dsp2-env /bin/bash
```