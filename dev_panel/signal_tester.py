import sys
import os
import argparse
import json
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt

# Garante que o Python encontra o modulo dsp2 na raiz do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import dsp2._dsp2_core as core
from dsp2.graph_loader import GraphLoader
from dsp2.constants import DEFAULT_SAMPLE_RATE, DEFAULT_BLOCK_SIZE

def calculate_signal_metrics(samples):
    values = np.asarray(samples, dtype=float)
    if values.size == 0:
        return {
            "min": None,
            "max": None,
            "rms": None,
            "peak": None,
            "dc_offset": None,
        }

    return {
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "rms": float(np.sqrt(np.mean(values * values))),
        "peak": float(np.max(np.abs(values))),
        "dc_offset": float(np.mean(values)),
    }

def _format_metric(value):
    if value is None:
        return "n/a"
    return f"{value:.6g}"

def _escape_markdown_cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")

def _log_level_name(log):
    return "INFO" if log.level == core.LogLevel.INFO else "ERROR"

def build_markdown_report(
    graph_data,
    node_ids,
    captured_data,
    logs,
    graph_path,
    output_path,
    sample_rate,
    block_size,
    num_blocks,
):
    lines = [
        "# D(SP)^2 - Relatorio de Simulacao do Grafo",
        "",
        f"- Gerado em: {datetime.now().isoformat(timespec='seconds')}",
        f"- Grafo: `{graph_path}`",
        f"- Imagem: `{output_path}`",
        f"- Blocos processados: `{num_blocks}`",
        f"- Sample rate configurado: `{sample_rate}` Hz",
        f"- Block size configurado: `{block_size}` amostras",
        "",
        "## Nos",
        "",
        "| Nome | Tipo | ID C++ |",
        "| --- | --- | ---: |",
    ]

    for node in graph_data.get("nodes", []):
        name = node.get("name", "")
        node_type = node.get("type", "")
        node_id = node_ids.get(name, "n/a")
        lines.append(
            "| "
            + " | ".join(
                [
                    _escape_markdown_cell(name),
                    _escape_markdown_cell(node_type),
                    _escape_markdown_cell(node_id),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Conexoes",
            "",
            "| Origem | Porta Origem | Destino | Porta Destino |",
            "| --- | ---: | --- | ---: |",
        ]
    )

    for edge in graph_data.get("edges", []):
        lines.append(
            "| "
            + " | ".join(
                [
                    _escape_markdown_cell(edge.get("source", "")),
                    _escape_markdown_cell(edge.get("source_port", "")),
                    _escape_markdown_cell(edge.get("dest", "")),
                    _escape_markdown_cell(edge.get("dest_port", "")),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Saidas e Metricas",
            "",
            "| No | Porta | Amostras | Sample Rate Real (Hz) | Min | Max | RMS | Peak | DC Offset |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    for node_name, ports in captured_data.items():
        for port, payload in ports.items():
            samples = payload["samples"]
            metrics = calculate_signal_metrics(samples)
            lines.append(
                "| "
                + " | ".join(
                    [
                        _escape_markdown_cell(node_name),
                        str(port),
                        str(len(samples)),
                        _format_metric(payload["sample_rate"]),
                        _format_metric(metrics["min"]),
                        _format_metric(metrics["max"]),
                        _format_metric(metrics["rms"]),
                        _format_metric(metrics["peak"]),
                        _format_metric(metrics["dc_offset"]),
                    ]
                )
                + " |"
            )

    lines.extend(["", "## Logs C++", ""])
    if logs:
        lines.extend(["| Nivel | Mensagem |", "| --- | --- |"])
        for log in logs:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _escape_markdown_cell(_log_level_name(log)),
                        _escape_markdown_cell(log.message),
                    ]
                )
                + " |"
            )
    else:
        lines.append("Nenhum evento foi coletado do Ring Buffer C++.")

    lines.append("")
    return "\n".join(lines)

class DSP2TestHarness:
    def __init__(self, sample_rate, block_size):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.engine = core.Engine()
        self.engine.set_signal_parameters(self.sample_rate, self.block_size)
        self.node_ids = {}
        self.graph_data = {}

    def load_graph(self, json_path):
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Erro: O ficheiro JSON '{json_path}' nao foi encontrado.")
        with open(json_path, "r", encoding="utf-8") as f:
            self.graph_data = json.load(f)
        self.node_ids = GraphLoader.load_from_json(self.engine, json_path)

    def run_and_capture(self, num_blocks):
        print(f"[Tester] A preparar memoria C++ para {num_blocks} blocos...")
        core.get_logs()
        self.engine.prepare_engine()

        # Dicionario para armazenar o sinal continuo de cada no e porta de saida.
        captured_data = {}
        for name, node_id in self.node_ids.items():
            port_count = self.engine.get_node_output_port_count(node_id)
            captured_data[name] = {}
            for port in range(port_count):
                captured_data[name][port] = {
                    "samples": [],
                    "sample_rate": self.engine.get_node_output_sample_rate(node_id, port),
                }

        # Ciclo de Tempo Real Simulado
        for i in range(num_blocks):
            self.engine.process_block()
            
            # Puxa o output de TODOS os nos/portas e concatena
            for name, node_id in self.node_ids.items():
                for port in captured_data[name].keys():
                    buffer_out = self.engine.get_node_output(node_id, port)
                    captured_data[name][port]["samples"].extend(buffer_out)

        logs = self._collect_cpp_logs()
        return captured_data, logs

    def _collect_cpp_logs(self):
        """Verifica o Logger Lock-Free do C++ em busca de falhas silenciosas."""
        logs = core.get_logs()
        if logs:
            print("\n[Aviso C++] Foram detetados eventos no motor de audio:")
            for log in logs:
                print(f" -> [{_log_level_name(log)}] {log.message}")
        else:
            print("[C++] Motor operou de forma limpa (sem erros de RingBuffer).")
        return logs

    def plot_results(self, data, output_path):
        num_nodes = len(data)
        if num_nodes == 0:
            print("Nenhum dado capturado para gerar o grafico.")
            return

        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # Ajusta a altura da imagem dinamicamente com base no numero de nos
        fig, axs = plt.subplots(num_nodes, 1, figsize=(12, 2.5 * num_nodes), sharex=True)
        fig.suptitle(f'D(SP)^2 - Inspecao Universal do Grafo', fontsize=14)

        # Garante que axs seja iteravel mesmo se houver apenas 1 no
        if num_nodes == 1:
            axs = [axs]

        colors = plt.cm.tab10(np.linspace(0, 1, num_nodes))

        # Gera os sub-graficos dinamicamente
        for ax, (node_name, ports), color in zip(axs, data.items(), colors):
            # 1. Descobre o ID do no usando o dicionario da classe
            port_data = ports.get(0, {"samples": [], "sample_rate": 0.0})
            signal = port_data["samples"]
            
            # 2. Puxa a taxa de amostragem real negociada no C++ (SDF Multirate)
            sample_rate = port_data["sample_rate"]
            
            # 3. Aplica a fisica (t = n / Fs) se a taxa for valida
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
        plt.close(fig)
        print(f"\n[Tester] Validacao visual guardada em: {output_path}")

    def write_report(self, report_path, data, logs, graph_path, output_path, num_blocks):
        report_dir = os.path.dirname(report_path)
        if report_dir:
            os.makedirs(report_dir, exist_ok=True)

        report = build_markdown_report(
            self.graph_data,
            self.node_ids,
            data,
            logs,
            graph_path,
            output_path,
            self.sample_rate,
            self.block_size,
            num_blocks,
        )

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"[Tester] Relatorio de simulacao guardado em: {report_path}")

def main():
    parser = argparse.ArgumentParser(description="Test Harness Robusto para o D(SP)^2")
    parser.add_argument("-g", "--graph", type=str, required=True, help="Caminho para o ficheiro JSON do grafo")
    parser.add_argument("-o", "--output", type=str, default="dev_panel/test_output.png", help="Caminho de destino do grafico (ex: result.png)")
    parser.add_argument("-b", "--blocks", type=int, default=1, help="Numero de blocos de audio a processar")
    parser.add_argument("-sr", "--samplerate", type=float, default=DEFAULT_SAMPLE_RATE, help="Taxa de Amostragem (Sample Rate)")
    parser.add_argument("-bs", "--blocksize", type=int, default=DEFAULT_BLOCK_SIZE, help="Tamanho do Bloco (Block Size)")
    parser.add_argument("--report", type=str, default=None, help="Caminho de destino do relatorio Markdown")
    
    args = parser.parse_args()

    tester = DSP2TestHarness(args.samplerate, args.blocksize)
    
    try:
        tester.load_graph(args.graph)
        data, logs = tester.run_and_capture(args.blocks)
        tester.plot_results(data, args.output)
        if args.report:
            tester.write_report(args.report, data, logs, args.graph, args.output, args.blocks)
    except Exception as e:
        print(f"\n[Falha Critica] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
