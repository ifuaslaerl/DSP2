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

class DSP2Orchestrator:
    def __init__(self):
        print("--- Inicializando Orquestrador D(SP)^2 ---")
        self.engine = core.Engine()
        self.is_running = False
        self.log_thread = None
        
        # Consome as constantes globais
        self.engine.set_audio_parameters(DEFAULT_SAMPLE_RATE, DEFAULT_BLOCK_SIZE)

    def _poll_logs(self):
        """
        Thread secundária: Monitoriza o C++ Ring Buffer.
        Não bloqueia a execução do motor de áudio.
        """
        while self.is_running:
            logs = core.get_logs()
            for log in logs:
                # Mapeia o Enum do C++ para texto
                level_str = "INFO" if log.level == core.LogLevel.INFO else "ERROR"
                print(f"[Core C++ | {level_str}] {log.message}")
            
            time.sleep(POLLING_INTERVAL_SEC) # Pausa baseada na constante

    def run_simulation(self, duration_seconds=DEFAULT_SIMULATION_DURATION):
        """
        Thread principal: Orquestra a compilação do grafo e o ciclo de áudio.
        """
        print("[Python] Preparando Engine (Alocação de Memória C++)...")
        self.engine.prepare_engine()

        # Inicia a thread de monitorização de Logs
        self.is_running = True
        self.log_thread = threading.Thread(target=self._poll_logs, daemon=True)
        self.log_thread.start()

        print(f"[Python] Iniciando processamento de áudio ({duration_seconds}s)...")
        
        # Calcula blocos com base nas constantes
        total_blocks = int((duration_seconds * DEFAULT_SAMPLE_RATE) / DEFAULT_BLOCK_SIZE)

        try:
            # LOOP DE TEMPO REAL (Simulado em Python)
            for _ in range(total_blocks):
                # O C++ processa a matemática do bloco
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
        print("--- Processamento Encerrado ---")

    def run_simulation(self, duration_seconds=DEFAULT_SIMULATION_DURATION):
        # 1. NOVO: Carrega o Grafo dinamicamente antes do prepare()!
        GraphLoader.load_from_json(self.engine, 'tests/graph_test.json')
        
        print("[Python] Preparando Engine (Aloca o de Mem ria C++)...")
        self.engine.prepare_engine()


if __name__ == "__main__":
    app = DSP2Orchestrator()
    app.run_simulation()