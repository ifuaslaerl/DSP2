import argparse
import os
import sys
from datetime import datetime

# Garante que o Python encontra o modulo dsp2 na raiz do projeto.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import dsp2._dsp2_core as core
from dsp2.constants import DEFAULT_BLOCK_SIZE, DEFAULT_SAMPLE_RATE
from dev_panel.signal_tester import (
    DSP2TestHarness,
    calculate_signal_metrics,
)


METRIC_NAMES = ("min", "max", "rms", "peak", "dc_offset")


def format_report_value(value):
    if value is None:
        return "n/a"
    return f"{value:.6g}"


def escape_markdown_cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def log_level_name(log):
    return "INFO" if log.level == core.LogLevel.INFO else "ERROR"


def calculate_delta(baseline_value, candidate_value):
    if baseline_value is None or candidate_value is None:
        return {"absolute": None, "percent": None}

    absolute = candidate_value - baseline_value
    if baseline_value == 0:
        percent = None
    else:
        percent = (absolute / abs(baseline_value)) * 100.0

    return {"absolute": absolute, "percent": percent}


def flatten_capture(captured_data):
    flattened = {}
    for node_name, ports in captured_data.items():
        for port, payload in ports.items():
            samples = payload["samples"]
            flattened[(node_name, port)] = {
                "sample_count": len(samples),
                "sample_rate": payload["sample_rate"],
                "metrics": calculate_signal_metrics(samples),
            }
    return flattened


def compare_captures(baseline_data, candidate_data):
    baseline = flatten_capture(baseline_data)
    candidate = flatten_capture(candidate_data)
    keys = sorted(set(baseline.keys()) | set(candidate.keys()))

    comparisons = []
    for node_name, port in keys:
        baseline_payload = baseline.get((node_name, port))
        candidate_payload = candidate.get((node_name, port))

        status = "ok"
        if baseline_payload is None:
            status = "missing_baseline"
        elif candidate_payload is None:
            status = "missing_candidate"

        baseline_metrics = (
            baseline_payload["metrics"] if baseline_payload is not None else {}
        )
        candidate_metrics = (
            candidate_payload["metrics"] if candidate_payload is not None else {}
        )

        comparisons.append(
            {
                "node": node_name,
                "port": port,
                "status": status,
                "baseline": baseline_payload,
                "candidate": candidate_payload,
                "rms_delta": calculate_delta(
                    baseline_metrics.get("rms"), candidate_metrics.get("rms")
                ),
                "peak_delta": calculate_delta(
                    baseline_metrics.get("peak"), candidate_metrics.get("peak")
                ),
            }
        )

    return comparisons


def run_simulation(graph_path, sample_rate, block_size, num_blocks):
    tester = DSP2TestHarness(sample_rate, block_size)
    tester.load_graph(graph_path)
    captured_data, logs = tester.run_and_capture(num_blocks)
    return captured_data, logs


def build_comparison_report(
    comparisons,
    baseline_logs,
    candidate_logs,
    baseline_path,
    candidate_path,
    sample_rate,
    block_size,
    num_blocks,
):
    lines = [
        "# D(SP)^2 - Comparador de Simulacoes do Grafo",
        "",
        f"- Gerado em: {datetime.now().isoformat(timespec='seconds')}",
        f"- Baseline: `{baseline_path}`",
        f"- Candidate: `{candidate_path}`",
        f"- Blocos processados por simulacao: `{num_blocks}`",
        f"- Sample rate configurado: `{sample_rate}` Hz",
        f"- Block size configurado: `{block_size}` amostras",
        "",
        "## Comparacao por Saida",
        "",
        "| No | Porta | Status | Amostras Base | Amostras Cand | Fs Base | Fs Cand | RMS Base | RMS Cand | Delta RMS | Delta RMS % | Peak Base | Peak Cand | Delta Peak | Delta Peak % |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    missing = []
    for item in comparisons:
        baseline = item["baseline"]
        candidate = item["candidate"]
        baseline_metrics = baseline["metrics"] if baseline else {}
        candidate_metrics = candidate["metrics"] if candidate else {}

        if item["status"] != "ok":
            missing.append(item)

        lines.append(
            "| "
            + " | ".join(
                [
                    escape_markdown_cell(item["node"]),
                    str(item["port"]),
                    item["status"],
                    str(baseline["sample_count"]) if baseline else "n/a",
                    str(candidate["sample_count"]) if candidate else "n/a",
                    format_report_value(baseline["sample_rate"] if baseline else None),
                    format_report_value(candidate["sample_rate"] if candidate else None),
                    format_report_value(baseline_metrics.get("rms")),
                    format_report_value(candidate_metrics.get("rms")),
                    format_report_value(item["rms_delta"]["absolute"]),
                    format_report_value(item["rms_delta"]["percent"]),
                    format_report_value(baseline_metrics.get("peak")),
                    format_report_value(candidate_metrics.get("peak")),
                    format_report_value(item["peak_delta"]["absolute"]),
                    format_report_value(item["peak_delta"]["percent"]),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Metricas Completas",
            "",
            "| No | Porta | Lado | Min | Max | RMS | Peak | DC Offset |",
            "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    for item in comparisons:
        for side_name, payload in (
            ("baseline", item["baseline"]),
            ("candidate", item["candidate"]),
        ):
            metrics = payload["metrics"] if payload else {}
            lines.append(
                "| "
                + " | ".join(
                    [
                        escape_markdown_cell(item["node"]),
                        str(item["port"]),
                        side_name,
                        format_report_value(metrics.get("min")),
                        format_report_value(metrics.get("max")),
                        format_report_value(metrics.get("rms")),
                        format_report_value(metrics.get("peak")),
                        format_report_value(metrics.get("dc_offset")),
                    ]
                )
                + " |"
            )

    lines.extend(["", "## Sinais Faltantes", ""])
    if missing:
        lines.extend(["| No | Porta | Status |", "| --- | ---: | --- |"])
        for item in missing:
            lines.append(f"| {escape_markdown_cell(item['node'])} | {item['port']} | {item['status']} |")
    else:
        lines.append("Todos os sinais foram pareados por nome e porta.")

    lines.extend(["", "## Logs Baseline", ""])
    append_logs(lines, baseline_logs)

    lines.extend(["", "## Logs Candidate", ""])
    append_logs(lines, candidate_logs)

    lines.append("")
    return "\n".join(lines)


def append_logs(lines, logs):
    if logs:
        lines.extend(["| Nivel | Mensagem |", "| --- | --- |"])
        for log in logs:
            lines.append(
                f"| {escape_markdown_cell(log_level_name(log))} | {escape_markdown_cell(log.message)} |"
            )
    else:
        lines.append("Nenhum evento foi coletado do Ring Buffer C++.")


def write_comparison_report(output_path, report):
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)


def main():
    parser = argparse.ArgumentParser(description="Comparador de simulacoes D(SP)^2")
    parser.add_argument("--baseline", required=True, help="JSON do grafo baseline")
    parser.add_argument("--candidate", required=True, help="JSON do grafo candidate")
    parser.add_argument(
        "-o",
        "--output",
        default="dev_panel/comparison_report.md",
        help="Caminho de destino do relatorio Markdown",
    )
    parser.add_argument(
        "-b",
        "--blocks",
        type=int,
        default=1,
        help="Numero de blocos de audio por simulacao",
    )
    parser.add_argument(
        "-sr",
        "--samplerate",
        type=float,
        default=DEFAULT_SAMPLE_RATE,
        help="Taxa de Amostragem",
    )
    parser.add_argument(
        "-bs",
        "--blocksize",
        type=int,
        default=DEFAULT_BLOCK_SIZE,
        help="Tamanho do Bloco",
    )

    args = parser.parse_args()

    try:
        baseline_data, baseline_logs = run_simulation(
            args.baseline, args.samplerate, args.blocksize, args.blocks
        )
        candidate_data, candidate_logs = run_simulation(
            args.candidate, args.samplerate, args.blocksize, args.blocks
        )
        comparisons = compare_captures(baseline_data, candidate_data)
        report = build_comparison_report(
            comparisons,
            baseline_logs,
            candidate_logs,
            args.baseline,
            args.candidate,
            args.samplerate,
            args.blocksize,
            args.blocks,
        )
        write_comparison_report(args.output, report)
        print(f"[Comparator] Relatorio de comparacao guardado em: {args.output}")
    except Exception as exc:
        print(f"\n[Falha Critica] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
