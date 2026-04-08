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

## **Modo de Uso**

Todo o desenvolvimento, a compilação do motor em C++ e a execução da interface em Python devem ser feitos exclusivamente dentro do contêiner para garantir a reprodutibilidade do sistema em tempo real.

```bash
# Para entrar no terminal interativo do Docker
sudo docker-compose exec dsp2-env /bin/bash
```