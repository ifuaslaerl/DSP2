import sys
import os
import argparse
import json
import struct
import wave
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

def normalize_samples_for_wav(samples):
    values = np.asarray(samples, dtype=np.float32)
    if values.size == 0:
        return values

    peak = float(np.max(np.abs(values)))
    if peak <= 0.0:
        return values

    return values / peak

def resolve_wav_output_paths(output_prefix, wav_format):
    if wav_format == "pcm16":
        return {"pcm16": f"{output_prefix}_pcm16.wav"}
    if wav_format == "float32":
        return {"float32": f"{output_prefix}_float32.wav"}
    return {
        "pcm16": f"{output_prefix}_pcm16.wav",
        "float32": f"{output_prefix}_float32.wav",
    }

def write_pcm16_wav(path, samples, sample_rate):
    output_dir = os.path.dirname(path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    clipped = np.clip(samples, -1.0, 1.0)
    pcm = np.round(clipped * 32767.0).astype("<i2")

    with wave.open(path, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(int(round(sample_rate)))
        wav.writeframes(pcm.tobytes())

def write_float32_wav(path, samples, sample_rate):
    output_dir = os.path.dirname(path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    payload = np.asarray(samples, dtype="<f4").tobytes()
    byte_rate = int(round(sample_rate)) * 4
    block_align = 4
    fmt_chunk_size = 16
    audio_format_ieee_float = 3
    data_chunk_size = len(payload)
    riff_size = 4 + (8 + fmt_chunk_size) + (8 + data_chunk_size)

    with open(path, "wb") as wav:
        wav.write(b"RIFF")
        wav.write(struct.pack("<I", riff_size))
        wav.write(b"WAVE")
        wav.write(b"fmt ")
        wav.write(struct.pack("<IHHIIHH", fmt_chunk_size, audio_format_ieee_float, 1, int(round(sample_rate)), byte_rate, block_align, 32))
        wav.write(b"data")
        wav.write(struct.pack("<I", data_chunk_size))
        wav.write(payload)

def export_wav_files(captured_data, node_name, port, output_prefix, wav_format):
    if node_name not in captured_data:
        raise ValueError(f"No '{node_name}' nao encontrado nos dados capturados.")
    if port not in captured_data[node_name]:
        raise ValueError(f"Porta {port} nao encontrada no no '{node_name}'.")

    payload = captured_data[node_name][port]
    sample_rate = payload["sample_rate"]
    samples = normalize_samples_for_wav(payload["samples"])
    output_paths = resolve_wav_output_paths(output_prefix, wav_format)

    if "pcm16" in output_paths:
        write_pcm16_wav(output_paths["pcm16"], samples, sample_rate)
    if "float32" in output_paths:
        write_float32_wav(output_paths["float32"], samples, sample_rate)

    return {
        "node": node_name,
        "port": port,
        "sample_rate": sample_rate,
        "sample_count": int(samples.size),
        "normalization": "peak",
        "files": output_paths,
    }

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
    wav_export=None,
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

    if wav_export is not None:
        lines.extend(
            [
                "",
                "## Export WAV",
                "",
                f"- No: `{wav_export['node']}`",
                f"- Porta: `{wav_export['port']}`",
                f"- Sample rate real: `{_format_metric(wav_export['sample_rate'])}` Hz",
                f"- Amostras exportadas: `{wav_export['sample_count']}`",
                f"- Normalizacao: `{wav_export['normalization']}`",
                "",
                "| Formato | Arquivo |",
                "| --- | --- |",
            ]
        )
        for format_name, path in wav_export["files"].items():
            lines.append(f"| {format_name} | `{_escape_markdown_cell(path)}` |")

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

    def write_report(self, report_path, data, logs, graph_path, output_path, num_blocks, wav_export=None):
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
            wav_export,
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
    parser.add_argument("--wav-node", type=str, default=None, help="Nome visual do no a exportar para WAV")
    parser.add_argument("--wav-port", type=int, default=0, help="Porta de saida do no a exportar para WAV")
    parser.add_argument("--wav-output", type=str, default=None, help="Prefixo dos arquivos WAV gerados")
    parser.add_argument("--wav-format", choices=["pcm16", "float32", "both"], default="pcm16", help="Formato WAV a exportar")
    
    args = parser.parse_args()

    tester = DSP2TestHarness(args.samplerate, args.blocksize)
    
    try:
        tester.load_graph(args.graph)
        data, logs = tester.run_and_capture(args.blocks)
        tester.plot_results(data, args.output)
        wav_export = None
        if args.wav_node or args.wav_output:
            if not args.wav_node or not args.wav_output:
                raise ValueError("--wav-node e --wav-output devem ser usados em conjunto.")
            wav_export = export_wav_files(
                data,
                args.wav_node,
                args.wav_port,
                args.wav_output,
                args.wav_format,
            )
            for format_name, path in wav_export["files"].items():
                print(f"[Tester] WAV {format_name} guardado em: {path}")
        if args.report:
            tester.write_report(args.report, data, logs, args.graph, args.output, args.blocks, wav_export)
    except Exception as e:
        print(f"\n[Falha Critica] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
