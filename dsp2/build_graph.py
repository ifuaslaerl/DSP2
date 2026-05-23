import time
import threading
import argparse
import dsp2._dsp2_core as core
from dsp2.graph_loader import GraphLoader
from dsp2.constants import (
    DEFAULT_SAMPLE_RATE, 
    DEFAULT_BLOCK_SIZE, 
    POLLING_INTERVAL_SEC, 
    DEFAULT_SIMULATION_DURATION
)

class DSP2Orchestrator:
    """Orquestra a simulação híbrida Python/C++ do D(SP)^2."""
    def __init__(self):
        self.engine = core.Engine()
        self.is_running = False
        self.log_thread = None
        self.engine.set_signal_parameters(DEFAULT_SAMPLE_RATE, DEFAULT_BLOCK_SIZE)

    def _poll_logs(self):
        """Consome o Ring Buffer de logs C++."""
        while self.is_running:
            logs = core.get_logs()
            for log in logs:
                level_str = "INFO" if log.level == core.LogLevel.INFO else "ERROR"
                print(f"[Core C++ | {level_str}] {log.message}")
            time.sleep(POLLING_INTERVAL_SEC)

    def run_simulation(self, graph_path, duration_seconds=DEFAULT_SIMULATION_DURATION):
        """Carrega o grafo especificado e processa blocos simulados."""
        print(f"--- Iniciando Simulação com: {graph_path} ---")
        
        # Carrega a topologia via GraphLoader
        GraphLoader.load_from_json(self.engine, graph_path)
        
        print("[Python] Preparando Engine...")
        self.engine.prepare_engine()
        
        self.is_running = True
        self.log_thread = threading.Thread(target=self._poll_logs, daemon=True)
        self.log_thread.start()
        
        total_blocks = int((duration_seconds * DEFAULT_SAMPLE_RATE) / DEFAULT_BLOCK_SIZE)
        
        try:
            for i in range(total_blocks):
                self.engine.process_block()
                time.sleep(DEFAULT_BLOCK_SIZE / DEFAULT_SAMPLE_RATE)
        except KeyboardInterrupt:
            print("\n[Python] Simulação interrompida.")
        finally:
            self.stop()

    def stop(self):
        self.is_running = False
        if self.log_thread:
            self.log_thread.join()
        print("--- Processamento Encerrado ---")

def main():
    parser = argparse.ArgumentParser(description="D(SP)^2: Motor de Simulação DSP")
    parser.add_argument(
        "--graph", 
        type=str, 
        default="tests/math_test.json", 
        help="Caminho para o arquivo JSON do grafo (padrão: tests/math_test.json)"
    )
    parser.add_argument(
        "--duration", 
        type=float, 
        default=DEFAULT_SIMULATION_DURATION, 
        help="Duração da simulação em segundos"
    )
    
    args = parser.parse_args()
    
    app = DSP2Orchestrator()
    app.run_simulation(graph_path=args.graph, duration_seconds=args.duration)

if __name__ == "__main__":
    main()