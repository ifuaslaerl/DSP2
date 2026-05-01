#pragma once
#include "../core/node_base.hpp"
#include "../core/node_factory.hpp"

// Nó Dummy 1: Um gerador genérico
template <typename T>
class DummyGenerator : public NodeBase<T> {
public:
    DummyGenerator() { this->output_buffers.resize(1, nullptr); }
    void prepare(double sr, int bs) override { this->output_buffers[0] = new T[bs]; }
    void process() override { /* Lógica matemática virá na fase 4 */ }
    ~DummyGenerator() { delete[] this->output_buffers[0]; }
};

// Nó Dummy 2: Um multiplicador (VCA/Ring Modulator) genérico
template <typename T>
class DummyMultiplier : public NodeBase<T> {
public:
    DummyMultiplier() {
        this->input_buffers.resize(2, nullptr);
        this->output_buffers.resize(1, nullptr);
    }
    void prepare(double sr, int bs) override { this->output_buffers[0] = new T[bs]; }
    void process() override { /* Lógica matemática virá na fase 4 */ }
    ~DummyMultiplier() { delete[] this->output_buffers[0]; }
};

// Auto-Registro no Singleton
inline void register_core_nodes() {
    NodeFactory<double>::get_instance().register_node("DummyGenerator", [](){ return new DummyGenerator<double>(); });
    NodeFactory<double>::get_instance().register_node("DummyMultiplier", [](){ return new DummyMultiplier<double>(); });
}