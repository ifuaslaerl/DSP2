#include <pybind11/pybind11.h>
#include <pybind11/stl.h> // Conversão automática de std::vector para list do Python
#include "../core/logger.hpp"
#include "../core/engine.hpp"

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
        .def("set_audio_parameters", &Engine<double>::set_audio_parameters)
        .def("prepare_engine", &Engine<double>::prepare_engine)
        .def("process_block", &Engine<double>::process_block)
        // ---> ADICIONE ESTAS DUAS LINHAS ABAIXO <---
        .def("add_node", &Engine<double>::add_node, "Adiciona um nó pelo nome da classe e retorna seu ID interno")
        .def("add_edge", &Engine<double>::add_edge, "Conecta a porta de saída de um nó à porta de entrada de outro");
}