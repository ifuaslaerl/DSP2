from .base import PyNode

class DebugNode(PyNode):
    def __init__(self):
        super().__init__()
        self.ticks = 0
        
        # [CORREÇÃO] Chamamos o método do C++ para alocar os vetores internos
        # O grafo de teste tem 1 entrada (Porta 0) e 1 saída (Porta 0)
        self.setup_buffers(1, 1)

    def compute_dimensions(self):
        print("[Python] DebugNode: compute_dimensions() chamado.")

    def prepare(self):
        print(f"[Python] DebugNode: prepare() chamado.")

    def process(self):
        self.ticks += 1
        if self.ticks % 100 == 0:
            print(f"[Python] DebugNode: process() executando no bloco {self.ticks}...")