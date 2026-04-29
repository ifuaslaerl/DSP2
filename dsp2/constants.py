"""
Constantes globais de configuração para o ambiente Python do D(SP)^2.
Devem refletir os padrões estabelecidos no core C++ (constants.hpp).
"""

# Parâmetros Globais de Áudio
DEFAULT_SAMPLE_RATE = 44100.0
DEFAULT_BLOCK_SIZE = 256

# Parâmetros do Orquestrador Híbrido (Tempo Real Simulado)
POLLING_INTERVAL_SEC = 0.05         # Frequência com que o Python verifica o Logger SPSC
DEFAULT_SIMULATION_DURATION = 2.0   # Tempo padrão de duração do ciclo de teste