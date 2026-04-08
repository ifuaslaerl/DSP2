# Arquivo escrito pelo Gemini pro
FROM ubuntu:22.04

# Evitar interações manuais durante a instalação de pacotes
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependências para o C++ (Core), CMake e Python (Interface)
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    python3 \
    python3-pip \
    python3-venv \
    git \
    && rm -rf /var/lib/apt/lists/*

# Configurar o diretório de trabalho padrão do contêiner
WORKDIR /app

# Manter o contêiner rodando em background
CMD ["/bin/bash"]