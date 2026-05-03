"""
Constantes globais de configuracao para o ambiente Python do D(SP)^2.
Devem refletir os padroes estabelecidos no core C++ (constants.hpp).
"""

# Parametros Globais de Audio
DEFAULT_SAMPLE_RATE = 44100.0
DEFAULT_BLOCK_SIZE = 256

# Parametros do Orquestrador Hibrido (Tempo Real Simulado)
POLLING_INTERVAL_SEC = 0.05         # Frequencia com que o Python verifica o Logger SPSC
DEFAULT_SIMULATION_DURATION = 2.0   # Tempo padrao de duracao do ciclo de teste
