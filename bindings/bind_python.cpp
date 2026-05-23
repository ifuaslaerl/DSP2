#include <pybind11/pybind11.h>
#include <pybind11/stl.h> // Conversão automática de std::vector para list do Python
#include "../core/logger.hpp"
#include "../core/engine.hpp"
#include "../core/node_base.hpp"

// Classe Trampolim para permitir herança e polimorfismo no Python
class PyNodeBase : public NodeBase<double> {
public:
    using NodeBase<double>::NodeBase; // Herda construtores

    void compute_dimensions() override {
        PYBIND11_OVERRIDE_PURE(
            void,
            NodeBase<double>,
            compute_dimensions
        );
    }

    void prepare() override {
        PYBIND11_OVERRIDE_PURE(
            void,
            NodeBase<double>,
            prepare
        );
    }

    void process() override {
        PYBIND11_OVERRIDE_PURE(
            void,
            NodeBase<double>,
            process
        );
    }

    void set_parameter(const std::string& param_name, double value) override {
        PYBIND11_OVERRIDE(
            void,
            NodeBase<double>,
            set_parameter,
            param_name,
            value
        );
    }

    void set_parameter_array(const std::string& param_name, const std::vector<double>& values) override {
        PYBIND11_OVERRIDE(
            void,
            NodeBase<double>,
            set_parameter_array,
            param_name,
            values
        );
    }
};

namespace py = pybind11;

/**
 * @brief Função auxiliar para esvaziar o Ring Buffer e retornar os logs para o Python.
 * Como o pop() remove um item de cada vez, este wrapper simplifica a vida do 
 * desenvolvedor Python ao retornar uma lista com todas as mensagens pendentes.
 */
std::vector<DSP2Log::LogEvent> get_logs_wrapper() {
    std::vector<DSP2Log::LogEvent> logs;
    DSP2Log::LogEvent event;
    
    // Consome enquanto houver itens no Buffer Circular SPSC
    while (DSP2Log::Logger::get_instance().pop(event)) {
        logs.push_back(event);
    }
    return logs;
}

// Definição do módulo dsp2_core (nomeado conforme o CMakeLists.txt)
PYBIND11_MODULE(_dsp2_core, m) {
    m.doc() = "DSP2 Core: Ponte de ligação entre C++ de Tempo Real e Orquestração Python";

    // --- Exposição do Sistema de Logging ---
    
    py::enum_<DSP2Log::Level>(m, "LogLevel")
        .value("INFO", DSP2Log::Level::INFO)
        .value("ERROR", DSP2Log::Level::ERROR)
        .export_values();

    py::class_<DSP2Log::LogEvent>(m, "LogEvent")
        .def_readonly("level", &DSP2Log::LogEvent::level)
        // Convertemos const char* para std::string explicitamente para o Python
        .def_property_readonly("message", [](const DSP2Log::LogEvent& e) {
            return std::string(e.message);
        });

    m.def("get_logs", &get_logs_wrapper, "Retorna uma lista com todos os logs acumulados no Core.");
    
    // --- Exposição do Engine (Fase de Simulação) ---
    
    // Vinculamos a versão <double> para uso no Python/Simulação
    py::class_<Engine<double>>(m, "Engine")
        .def(py::init<>())
        .def("set_signal_parameters", &Engine<double>::set_signal_parameters)
        .def("prepare_engine", &Engine<double>::prepare_engine)
        .def("process_block", &Engine<double>::process_block)
        .def("add_node", &Engine<double>::add_node, "Adiciona um nó pelo nome da classe e retorna seu ID interno")
        // [NOVO] Adiciona a injeção de nós em Python! 
        // py::keep_alive<1, 2>() diz ao Python para não apagar (Garbage Collect) o nó enquanto o Engine (1) existir.
        .def("add_node_obj", &Engine<double>::add_node_ptr, py::keep_alive<1, 2>(), "Injeta um objeto nó instanciado no Python")        
        .def("add_edge", &Engine<double>::add_edge, "Conecta a porta de saída de um nó à porta de entrada de outro")
        .def("set_node_parameter", &Engine<double>::set_node_parameter, "Define um parametro base do no")
        .def("get_node_output", &Engine<double>::get_node_output, "Retorna uma copia do buffer de saida de um no")
        .def("set_node_parameter_array", &Engine<double>::set_node_parameter_array, "Define um array de parametros para o no")
        .def("get_node_output_sample_rate", &Engine<double>::get_node_output_sample_rate, "Retorna a taxa de amostragem física (Hz) de uma porta de saída")
        .def("get_node_output_port_count", &Engine<double>::get_node_output_port_count, "Retorna a quantidade de portas de saída de um no");

    // --- Exposição do NodeBase (Fase 4.2: Vértices Python) ---
    py::class_<NodeBase<double>, PyNodeBase>(m, "NodeBase")
        .def(py::init<>())
        .def("setup_buffers", &NodeBase<double>::setup_buffers)
        .def("compute_dimensions", &NodeBase<double>::compute_dimensions)
        .def("prepare", &NodeBase<double>::prepare)
        .def("process", &NodeBase<double>::process)
        .def("set_parameter", &NodeBase<double>::set_parameter)
        .def("set_parameter_array", &NodeBase<double>::set_parameter_array);

    
}
