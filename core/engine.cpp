#include "engine.hpp"
#include "node_factory.hpp"

// Headers antigos
#include "../nodes_cpp/math_nodes.hpp"
#include "../nodes_cpp/oscillator_nodes.hpp"
#include "../nodes_cpp/noise_generator.hpp"
#include "../nodes_cpp/audio_file_input.hpp"

// [NOVO] Headers dos Vértices Avançados
#include "../nodes_cpp/decimator.hpp"
#include "../nodes_cpp/windowing.hpp"
#include "../nodes_cpp/butterworth_filter.hpp"
#include "../nodes_cpp/convolution.hpp"
#include "../nodes_cpp/quadrature_modulator.hpp"
#include "../nodes_cpp/spectrum_analyser.hpp"
#include "../nodes_cpp/spectral_peak_picker.hpp"
#include "../nodes_cpp/harmonic_pitch_detector.hpp"
#include "../nodes_cpp/frequency_to_midi_note.hpp"

// ==========================================
// Função Global de Registro de Nós
// ==========================================

void register_core_nodes() {
    // Nós de Teste e Básicos
    NodeFactory<double>::get_instance().register_node("Add", [](){ return new AddNode<double>(); });
    NodeFactory<double>::get_instance().register_node("Multiply", [](){ return new MultiplyNode<double>(); });
    NodeFactory<double>::get_instance().register_node("Gain", [](){ return new GainNode<double>(); });
    NodeFactory<double>::get_instance().register_node("Constant", [](){ return new ConstantNode<double>(); });
    NodeFactory<double>::get_instance().register_node("SineOscillator", [](){ return new SineOscillator<double>(); });
    NodeFactory<double>::get_instance().register_node("NoiseGenerator", [](){ return new NoiseGenerator<double>(); });
    NodeFactory<double>::get_instance().register_node("AudioFileInput", [](){ return new AudioFileInput<double>(); });

    // [NOVO] Nós Avançados (SDF, FIR, IIR, I/Q)
    NodeFactory<double>::get_instance().register_node("Decimator", [](){ return new Decimator<double>(); });
    NodeFactory<double>::get_instance().register_node("Windowing", [](){ return new Windowing<double>(); });
    NodeFactory<double>::get_instance().register_node("ButterworthFilter", [](){ return new ButterworthFilter<double>(); });
    NodeFactory<double>::get_instance().register_node("Convolution", [](){ return new Convolution<double>(); });
    NodeFactory<double>::get_instance().register_node("QuadratureModulator", [](){ return new QuadratureModulator<double>(); });
    NodeFactory<double>::get_instance().register_node("SpectrumAnalyser", [](){ return new SpectrumAnalyser<double>(); });
    NodeFactory<double>::get_instance().register_node("SpectrumAnalyzer", [](){ return new SpectrumAnalyser<double>(); });
    NodeFactory<double>::get_instance().register_node("SpectralPeakPicker", [](){ return new SpectralPeakPicker<double>(); });
    NodeFactory<double>::get_instance().register_node("HarmonicPitchDetector", [](){ return new HarmonicPitchDetector<double>(); });
    NodeFactory<double>::get_instance().register_node("FrequencyToMidiNote", [](){ return new FrequencyToMidiNote<double>(); });
}

// ==========================================
// Construtor e Destrutor
// ==========================================

template <typename T>
Engine<T>::Engine()
    : graph(std::make_unique<Graph<T>>()),
      sampleRate(DSP2Config::DEFAULT_SAMPLE_RATE),
      blockSize(DSP2Config::DEFAULT_BLOCK_SIZE) {
    register_core_nodes();
}

template <typename T>
Engine<T>::~Engine() = default;

// ==========================================
// Configuração
// ==========================================

template <typename T>
void Engine<T>::set_signal_parameters(double sample_rate, int block_size) {
    sampleRate = sample_rate;
    blockSize = block_size;
}

// ==========================================
// Inicialização do Motor (Fora do Ciclo Crítico)
// ==========================================

template <typename T>
void Engine<T>::prepare_engine() {
    if (graph != nullptr) {
        // Dispara a ordenação topológica (Kosaraju), avaliação de DAG,
        // alocação de buffers nos nós e mapeamento de ponteiros Zero-Copy.
        graph->compile(sampleRate, blockSize);
    }
}

// ==========================================
// Callback de Áudio (Processamento de Bloco)
// ==========================================

template <typename T>
void Engine<T>::process_block() {
    if (graph != nullptr) {
        // STRICT REAL-TIME: Delega o processamento inteiramente ao Grafo.
        // Nenhuma alocação, lock ou syscall ocorre daqui para a frente.
        graph->process();
    }
}

template <typename T>
int Engine<T>::add_node(const std::string& node_type) {
    // Aloca memória dinamicamente apenas na fase de Setup
    NodeBase<T>* node = NodeFactory<T>::get_instance().create(node_type);
    if (!node) {
        DSP2_LOG_ERROR("NodeFactory: Falha ao criar no - Tipo desconhecido!");
        return -1; // Retorna erro para o Python lidar
    }
    graph->add_node(node);
    return graph->get_node_count() - 1; // Retorna o ID (índice) do nó criado
}

template <typename T>
void Engine<T>::add_edge(int src_id, int src_port, int dest_id, int dest_port) {
    if (graph != nullptr) {
        graph->add_edge(src_id, src_port, dest_id, dest_port);
    }
}

template <typename T>
std::vector<T> Engine<T>::get_node_output(int node_id, int port) {
    int actual_size = 0;
    if (graph != nullptr) {
        // Consulta o tamanho real daquela porta (Multirate)
        actual_size = graph->get_node_output_size(node_id, port);
    }

    // Se o nó não existir ou a porta for inválida, retorna vetor vazio
    if (actual_size <= 0) return std::vector<T>();

    // Aloca o vetor do Python com o tamanho EXATO da saída do nó
    std::vector<T> result(actual_size, static_cast<T>(0));

    if (graph != nullptr) {
        const T* buffer = graph->get_node_output_buffer(node_id, port);
        if (buffer != nullptr) {
            // Copia apenas a memória segura
            for (int i = 0; i < actual_size; ++i) {
                result[i] = buffer[i];
            }
        }
    }
    return result;
}

template <typename T>
void Engine<T>::set_node_parameter(int node_id, const std::string& param_name, double value) {
    if (graph != nullptr) {
        graph->set_node_parameter(node_id, param_name, value);
    }
}

template <typename T>
void Engine<T>::set_node_parameter_array(int node_id, const std::string& param_name, const std::vector<double>& values) {
    if (graph != nullptr) {
        graph->set_node_parameter_array(node_id, param_name, values);
    }
}

template <typename T>
double Engine<T>::get_node_output_sample_rate(int node_id, int port) {
    if (graph != nullptr) {
        return graph->get_node_output_sample_rate(node_id, port);
    }
    return 0.0;
}

template <typename T>
int Engine<T>::get_node_output_port_count(int node_id) {
    if (graph != nullptr) {
        return graph->get_node_output_port_count(node_id);
    }
    return 0;
}

// ==========================================
// Instanciação Explícita de Templates (Garante o linking)
// ==========================================

template class Engine<double>; // Para uso em SIMULATION (Python bindings)
template class Engine<float>;  // Para uso em EMBEDDED (Microcontroladores)
