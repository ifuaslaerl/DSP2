#!/usr/bin/env python3
"""
D(SP)^2 - Benchmark Híbrido e Comparador de Performance
Mede o tempo de execução e a assimetria entre duas topologias de grafos JSON.
"""

import sys
import os
import time
import argparse

# Garante que o Python enxergue o pacote 'dsp2' na raiz do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import dsp2._dsp2_core as core
from dsp2.graph_loader import GraphLoader
from dsp2.nodes_py.base import PyNode
import dsp2.graph_loader

# Utilitário Injetado: Nó de benchmark vazio para testes de overhead de GIL/Pybind11.
class PyBenchmarkNode(PyNode):
    def __init__(self):
        super().__init__()
        self.setup_buffers(1, 1)

    def process(self):
        pass

# INJEÇÃO CORRIGIDA: Registra o nó no dicionário do GraphLoader
dsp2.graph_loader.PYTHON_NODES["PyBenchmarkNode"] = PyBenchmarkNode


def run_benchmark_on_file(name, json_file, sample_rate, block_size, iterations):
    if not os.path.exists(json_file):
        raise FileNotFoundError(f"Arquivo não encontrado: {json_file}")
        
    engine = core.Engine()
    engine.set_signal_parameters(sample_rate, block_size)
    
    # Carrega a topologia (resolve Zero-Copy no C++ e aloca a memória)
    GraphLoader.load_from_json(engine, json_file)
    engine.prepare_engine()

    print(f"--- Executando: {name} ({os.path.basename(json_file)}) ---")
    
    # Aquecimento (Warmup - remove overhead de cache/JIT se houver)
    for _ in range(100):
        engine.process_block()

    # Benchmark de Tempo Real
    start_time = time.perf_counter()
    for _ in range(iterations):
        engine.process_block()
    end_time = time.perf_counter()
    
    elapsed = end_time - start_time
    blocks_per_sec = iterations / elapsed if elapsed > 0 else 0
    
    print(f"Tempo: {elapsed:.6f} s | Velocidade: {blocks_per_sec:.2f} blocos/s\n")
    return elapsed


def main():
    parser = argparse.ArgumentParser(description="D(SP)^2 - Comparador de Performance de Grafos")
    parser.add_argument("-b", "--baseline", required=True, help="Caminho para o JSON do grafo de referência (Baseline)")
    parser.add_argument("-c", "--candidate", required=True, help="Caminho para o JSON do grafo candidato a comparar")
    parser.add_argument("--blocks", type=int, default=250000, help="Número de blocos a processar")
    parser.add_argument("--block-size", type=int, default=512, help="Tamanho do bloco em amostras")
    parser.add_argument("--sample-rate", type=float, default=44100.0, help="Taxa de amostragem em Hz")
    
    args = parser.parse_args()

    print("==================================================")
    print("      D(SP)^2 - Profiler de Tempo de Execução     ")
    print("==================================================")
    print(f"Config: {args.blocks} Blocos | {args.block_size} Amostras/Bloco | Fs: {args.sample_rate}Hz\n")

    try:
        time_baseline = run_benchmark_on_file("Baseline", args.baseline, args.sample_rate, args.block_size, args.blocks)
        time_candidate = run_benchmark_on_file("Candidate", args.candidate, args.sample_rate, args.block_size, args.blocks)
    except Exception as e:
        print(f"[Erro Crítico] Falha na execução do benchmark: {e}")
        return

    ratio = time_candidate / time_baseline if time_baseline > 0 else 0
    diff_percent = ((time_candidate - time_baseline) / time_baseline) * 100 if time_baseline > 0 else 0
    
    print("==================================================")
    print("                    RESULTADOS                    ")
    print("==================================================")
    print(f"Baseline:   {time_baseline:.6f}s")
    print(f"Candidate:  {time_candidate:.6f}s")
    
    if diff_percent > 0:
        print(f"Assimetria: O candidato é {ratio:.2f}x MAIS LENTO (+{diff_percent:.1f}%)")
    elif diff_percent < 0:
        print(f"Assimetria: O candidato é {1/ratio:.2f}x MAIS RÁPIDO ({diff_percent:.1f}%)")
    else:
        print("Assimetria: Empate técnico (0%)")
    print("==================================================")


if __name__ == "__main__":
    main()