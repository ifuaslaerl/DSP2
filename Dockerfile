FROM ubuntu:22.04

# Evitar interações manuais durante a instalação de pacotes
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependências para o C++ (Core), CMake e Python (Interface)
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    git \
    pybind11-dev \
    && rm -rf /var/lib/apt/lists/*

# Configurar o diretório de trabalho padrão do contêiner
WORKDIR /app

# Shell interativo como processo principal do ambiente de desenvolvimento
CMD ["/bin/bash"]
