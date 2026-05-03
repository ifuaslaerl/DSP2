import sys
import os
import argparse
import numpy as np
import matplotlib.pyplot as plt

# Garante que o Python encontra o módulo dsp2 na raiz do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import dsp2._dsp2_core as core
from dsp2.graph_loader import GraphLoader
from dsp2.constants import DEFAULT_SAMPLE_RATE, DEFAULT_BLOCK_SIZE

class DSP2TestHarness:
    def __init__(self, sample_rate, block_size):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.engine = core.Engine()
        self.engine.set_signal_parameters(self.sample_rate, self.block_size)
        self.node_ids = {}

    def load_graph(self, json_path):
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Erro: O ficheiro JSON '{json_path}' não foi encontrado.")
        self.node_ids = GraphLoader.load_from_json(self.engine, json_path)

    def run_and_capture(self, num_blocks):
        print(f"[Tester] A preparar memória C++ para {num_blocks} blocos...")
        self.engine.prepare_engine()

        # Dicionário para armazenar o sinal contínuo de cada nó
        captured_data = {name: [] for name in self.node_ids.keys()}

        # Ciclo de Tempo Real Simulado
        for i in range(num_blocks):
            self.engine.process_block()
            
            # Puxa o output de TODOS os nós e concatena
            for name, node_id in self.node_ids.items():
                buffer_out = self.engine.get_node_output(node_id, 0)
                captured_data[name].extend(buffer_out)

        self._print_cpp_logs()
        return captured_data

    def _print_cpp_logs(self):
        """Verifica o Logger Lock-Free do C++ em busca de falhas silenciosas."""
        logs = core.get_logs()
        if logs:
            print("\n[Aviso C++] Foram detetados eventos no motor de áudio:")
            for log in logs:
                level_str = "INFO" if log.level == core.LogLevel.INFO else "ERROR"
                print(f" -> [{level_str}] {log.message}")
        else:
            print("[C++] Motor operou de forma limpa (sem erros de RingBuffer).")

    def plot_results(self, data, output_path):
        num_nodes = len(data)
        if num_nodes == 0:
            print("Nenhum dado capturado para gerar o gráfico.")
            return

        # Ajusta a altura da imagem dinamicamente com base no número de nós
        fig, axs = plt.subplots(num_nodes, 1, figsize=(12, 2.5 * num_nodes), sharex=True)
        fig.suptitle(f'D(SP)^2 - Inspeção Universal do Grafo', fontsize=14)

        # Garante que axs seja iterável mesmo se houver apenas 1 nó
        if num_nodes == 1:
            axs = [axs]

        colors = plt.cm.tab10(np.linspace(0, 1, num_nodes))

        # Gera os sub-gráficos dinamicamente
        for ax, (node_name, signal), color in zip(axs, data.items(), colors):
            # 1. Descobre o ID do nó usando o dicionário da classe
            node_id = self.node_ids[node_name]
            
            # 2. Puxa a taxa de amostragem real negociada no C++ (SDF Multirate)
            sample_rate = self.engine.get_node_output_sample_rate(node_id, 0)
            
            # 3. Aplica a física (t = n / Fs) se a taxa for válida
            if sample_rate > 0 and len(signal) > 0:
                time_axis = np.arange(len(signal)) / sample_rate
                ax.plot(time_axis, signal, color=color, label=f"{node_name} (Fs: {sample_rate}Hz)")
            else:
                # Fallback seguro
                ax.plot(signal, color=color, label=node_name)

            ax.legend(loc="upper right")
            ax.grid(True, linestyle='--', alpha=0.6)
            ax.set_ylabel('Amplitude f(x)')

        # 4. Atualiza o eixo X para refletir o tempo
        axs[-1].set_xlabel('Tempo x (Segundos)')
        
        plt.tight_layout()
        plt.savefig(output_path)
        print(f"\n[Tester] Validação visual guardada em: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Test Harness Robusto para o D(SP)^2")
    parser.add_argument("-g", "--graph", type=str, required=True, help="Caminho para o ficheiro JSON do grafo")
    parser.add_argument("-o", "--output", type=str, default="dev_panel/test_output.png", help="Caminho de destino do gráfico (ex: result.png)")
    parser.add_argument("-b", "--blocks", type=int, default=1, help="Número de blocos de áudio a processar")
    parser.add_argument("-sr", "--samplerate", type=float, default=DEFAULT_SAMPLE_RATE, help="Taxa de Amostragem (Sample Rate)")
    parser.add_argument("-bs", "--blocksize", type=int, default=DEFAULT_BLOCK_SIZE, help="Tamanho do Bloco (Block Size)")
    
    args = parser.parse_args()

    tester = DSP2TestHarness(args.samplerate, args.blocksize)
    
    try:
        tester.load_graph(args.graph)
        data = tester.run_and_capture(args.blocks)
        tester.plot_results(data, args.output)
    except Exception as e:
        print(f"\n[Falha Crítica] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()