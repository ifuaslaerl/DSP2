import dsp2._dsp2_core as core

class PyNode(core.NodeBase):
    """
    Classe base para todos os nós de DSP implementados em Python.
    Herda o ciclo de vida (compute_dimensions, prepare, process) da arquitetura C++ nativa.
    """
    def __init__(self):
        super().__init__()
        # Dicionário prático para armazenar parâmetros dinâmicos definidos via JSON
        self.parameters = {}

    def compute_dimensions(self):
        """
        Fase 1 (SDF): O nó avalia as dimensões de entrada e define as de saída.
        O comportamento padrão de um nó puro de controle em Python é não fazer nada,
        mas pode ser sobrescrito por nós que alteram a taxa de amostragem.
        """
        pass

    def prepare(self):
        """
        Fase 2: Alocação e Setup.
        Chamado uma única vez antes do loop de tempo real iniciar.
        """
        pass

    def process(self):
        """
        Fase 3: Tempo Real.
        Chamado a cada bloco pelo orquestrador C++.
        """
        pass

    def set_parameter(self, param_name: str, value: float):
        """Intercepta a configuração de parâmetros (escalares) vindos do GraphLoader."""
        self.parameters[param_name] = value

    def set_parameter_array(self, param_name: str, values: list):
        """Intercepta a configuração de parâmetros (arrays/listas) vindos do GraphLoader."""
        self.parameters[param_name] = values