import time
import threading
import dsp2._dsp2_core as core
from dsp2.graph_loader import GraphLoader

from dsp2.constants import (
    DEFAULT_SAMPLE_RATE, 
    DEFAULT_BLOCK_SIZE, 
    POLLING_INTERVAL_SEC, 
    DEFAULT_SIMULATION_DURATION
)

DEFAULT_GRAPH_PATH = "tests/math_test.json"


class DSP2Orchestrator:
    """Orquestra a simulacao hibrida Python/C++ do D(SP)^2.

    A classe mantem o Python responsavel por montar o grafo e consumir logs,
    enquanto o processamento de cada bloco permanece no core C++.
    """

    def __init__(self):
        print("--- Inicializando Orquestrador D(SP)^2 ---")
        self.engine = core.Engine()
        self.is_running = False
        self.log_thread = None
        
        # Consome as constantes globais
        self.engine.set_signal_parameters(DEFAULT_SAMPLE_RATE, DEFAULT_BLOCK_SIZE)

    def _poll_logs(self):
        """Consome o Ring Buffer de logs C++ sem bloquear o loop de audio."""
        while self.is_running:
            logs = core.get_logs()
            for log in logs:
                # Mapeia o Enum do C++ para texto
                level_str = "INFO" if log.level == core.LogLevel.INFO else "ERROR"
                print(f"[Core C++ | {level_str}] {log.message}")
            
            time.sleep(POLLING_INTERVAL_SEC) # Pausa baseada na constante

    def run_simulation(self, duration_seconds=DEFAULT_SIMULATION_DURATION):
        """Carrega o grafo padrao, prepara o engine e processa blocos simulados."""
        # O grafo precisa ser montado antes do prepare_engine(), pois a fase de
        # prepare aloca buffers e solda os ponteiros Zero-Copy no C++.
        GraphLoader.load_from_json(self.engine, DEFAULT_GRAPH_PATH)

        print("[Python] Preparando Engine (Alocacao de Memoria C++)...")
        self.engine.prepare_engine()

        # Inicia a thread de monitorizacao de Logs
        self.is_running = True
        self.log_thread = threading.Thread(target=self._poll_logs, daemon=True)
        self.log_thread.start()

        print(f"[Python] Iniciando processamento de audio ({duration_seconds}s)...")
        
        # Calcula blocos com base nas constantes
        total_blocks = int((duration_seconds * DEFAULT_SAMPLE_RATE) / DEFAULT_BLOCK_SIZE)

        try:
            # LOOP DE TEMPO REAL (Simulado em Python)
            for _ in range(total_blocks):
                # O C++ processa a matematica do bloco
                self.engine.process_block()
                
                # Simula o tempo do hardware
                time.sleep(DEFAULT_BLOCK_SIZE / DEFAULT_SAMPLE_RATE) 
                
        except KeyboardInterrupt:
            print("\n[Python] Interrompido pelo utilizador.")
        finally:
            self.stop()

    def stop(self):
        """Para as threads e limpa o ambiente."""
        self.is_running = False
        if self.log_thread:
            self.log_thread.join()
            self.log_thread = None
        print("--- Processamento Encerrado ---")


if __name__ == "__main__":
    app = DSP2Orchestrator()
    app.run_simulation()
