#pragma once
#include "../core/node_base.hpp"
#include "../core/node_factory.hpp"
#include "../core/buffer_ops.hpp"

/**
 * @class AddNode
 * @brief Somador LTI ponto a ponto (Mixer).
 * @note Entradas: Porta 0 e Porta 1 | Saídas: Porta 0
 */
template <typename T>
class AddNode : public NodeBase<T> {
public:
    AddNode() {
        this->input_buffers.resize(2, nullptr);
        this->output_buffers.resize(1, nullptr);
        
        this->input_block_sizes.resize(2, 0);
        this->output_block_sizes.resize(1, 0);
        this->input_sample_rates.resize(2, 0.0);
        this->output_sample_rates.resize(1, 0.0);
    }

    void compute_dimensions() override {
        // Assume que ambas as entradas têm o mesmo tamanho/taxa. Copia da Porta 0.
        if (this->input_block_sizes[0] > 0) {
            this->output_block_sizes[0] = this->input_block_sizes[0];
            this->output_sample_rates[0] = this->input_sample_rates[0];
        }
    }

    void prepare() override {
        this->output_buffers[0] = new T[this->output_block_sizes[0]];
    }

    void process() override {
        const T* __restrict in1 = this->input_buffers[0];
        const T* __restrict in2 = this->input_buffers[1];
        T* __restrict out = this->output_buffers[0];

        if (!in1 || !in2) return;

        // Copia in1 para out e soma in2 in-place (SIMD Otimizado)
        int size = this->output_block_sizes[0];
        for (int i = 0; i < size; ++i) out[i] = in1[i];
        DSP2BufferOps::add(out, in2, size);
    }

    ~AddNode() { delete[] this->output_buffers[0]; }
};

/**
 * @class MultiplyNode
 * @brief Multiplicador ponto a ponto (Ring Modulator / VCA).
 * @note Entradas: Porta 0 (Carrier) e Porta 1 (Modulator) | Saídas: Porta 0
 */
template <typename T>
class MultiplyNode : public NodeBase<T> {
public:
    MultiplyNode() {
        this->input_buffers.resize(2, nullptr);
        this->output_buffers.resize(1, nullptr);
        
        this->input_block_sizes.resize(2, 0);
        this->output_block_sizes.resize(1, 0);
        this->input_sample_rates.resize(2, 0.0);
        this->output_sample_rates.resize(1, 0.0);
    }

    void compute_dimensions() override {
        if (this->input_block_sizes[0] > 0) {
            this->output_block_sizes[0] = this->input_block_sizes[0];
            this->output_sample_rates[0] = this->input_sample_rates[0];
        }
    }

    void prepare() override {
        this->output_buffers[0] = new T[this->output_block_sizes[0]];
    }

    void process() override {
        const T* __restrict in1 = this->input_buffers[0];
        const T* __restrict in2 = this->input_buffers[1];
        T* __restrict out = this->output_buffers[0];

        if (!in1 || !in2) return;

        int size = this->output_block_sizes[0];
        for (int i = 0; i < size; ++i) out[i] = in1[i];
        DSP2BufferOps::multiply(out, in2, size);
    }

    ~MultiplyNode() { delete[] this->output_buffers[0]; }
};

/**
 * @class GainNode
 * @brief Aplica um ganho linear escalar.
 */
template <typename T>
class GainNode : public NodeBase<T> {
private:
    T gain = 1.0;
public:
    GainNode() {
        this->input_buffers.resize(1, nullptr);
        this->output_buffers.resize(1, nullptr);
        
        this->input_block_sizes.resize(1, 0);
        this->output_block_sizes.resize(1, 0);
        this->input_sample_rates.resize(1, 0.0);
        this->output_sample_rates.resize(1, 0.0);
    }

    void set_parameter(const std::string& param_name, double value) override {
        if (param_name == "gain") gain = static_cast<T>(value);
    }

    void compute_dimensions() override {
        if (this->input_block_sizes[0] > 0) {
            this->output_block_sizes[0] = this->input_block_sizes[0];
            this->output_sample_rates[0] = this->input_sample_rates[0];
        }
    }

    void prepare() override {
        this->output_buffers[0] = new T[this->output_block_sizes[0]];
    }

    void process() override {
        const T* __restrict in = this->input_buffers[0];
        T* __restrict out = this->output_buffers[0];

        if (!in) return;

        int size = this->output_block_sizes[0];
        for (int i = 0; i < size; ++i) out[i] = in[i];
        DSP2BufferOps::multiply_scalar(out, gain, size);
    }

    ~GainNode() { delete[] this->output_buffers[0]; }
};

/**
 * @class ConstantNode
 * @brief Gerador DC (Offset constante). Como é um gerador, não tem entradas.
 */
template <typename T>
class ConstantNode : public NodeBase<T> {
private:
    T value = 0.0;
public:
    ConstantNode() {
        this->output_buffers.resize(1, nullptr);
        // Geradores não precisam inicializar dimensões de entrada
        this->output_block_sizes.resize(1, 0);
        this->output_sample_rates.resize(1, 0.0);
    }

    void set_parameter(const std::string& param_name, double val) override {
        if (param_name == "value") value = static_cast<T>(val);
    }

    void compute_dimensions() override {
        // Nenhuma entrada para ler. As dimensões são injetadas pelo Motor em graph.cpp
    }

    void prepare() override {
        this->output_buffers[0] = new T[this->output_block_sizes[0]];
    }

    void process() override {
        T* __restrict out = this->output_buffers[0];
        int size = this->output_block_sizes[0];
        for (int i = 0; i < size; ++i) {
            out[i] = value;
        }
    }

    ~ConstantNode() { delete[] this->output_buffers[0]; }
};