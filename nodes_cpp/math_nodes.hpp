#pragma once

#include "../core/node_base.hpp"
#include "../core/node_factory.hpp"
#include "../core/constants.hpp"
#include "../core/logger.hpp"

// ==========================================
// 1. AddNode (Somador / Mixer Simples)
// ==========================================
template <typename T>
class AddNode : public NodeBase<T> {
private:
    int currentBlockSize = DSP2Config::DEFAULT_BLOCK_SIZE;
public:
    AddNode() {
        this->input_buffers.resize(2, nullptr);
        this->output_buffers.resize(1, nullptr);
    }
    void prepare(double /*sampleRate*/, int blockSize) override {
        currentBlockSize = blockSize;
        this->output_buffers[0] = new T[blockSize];
    }
    void process() override {
        const T* __restrict in1 = this->input_buffers[0];
        const T* __restrict in2 = this->input_buffers[1];
        T* __restrict out = this->output_buffers[0];

        if (!in1 || !in2) {
            DSP2_LOG_ERROR("AddNode: Buffers de entrada ausentes (Grafo desconectado).");
            return;
        }

        // Loop otimizado para SIMD (1 pass)
        for (int i = 0; i < currentBlockSize; ++i) {
            out[i] = in1[i] + in2[i];
        }
    }
    ~AddNode() { delete[] this->output_buffers[0]; }
};

// ==========================================
// 2. MultiplyNode (Modulador em Anel / VCA via sinal)
// ==========================================
template <typename T>
class MultiplyNode : public NodeBase<T> {
private:
    int currentBlockSize = DSP2Config::DEFAULT_BLOCK_SIZE;
public:
    MultiplyNode() {
        this->input_buffers.resize(2, nullptr);
        this->output_buffers.resize(1, nullptr);
    }
    void prepare(double /*sampleRate*/, int blockSize) override {
        currentBlockSize = blockSize;
        this->output_buffers[0] = new T[blockSize];
    }
    void process() override {
        const T* __restrict in1 = this->input_buffers[0];
        const T* __restrict in2 = this->input_buffers[1];
        T* __restrict out = this->output_buffers[0];

        if (!in1 || !in2) {
            DSP2_LOG_ERROR("MultiplyNode: Buffers de entrada ausentes.");
            return;
        }

        for (int i = 0; i < currentBlockSize; ++i) {
            out[i] = in1[i] * in2[i];
        }
    }
    ~MultiplyNode() { delete[] this->output_buffers[0]; }
};

// ==========================================
// 3. GainNode (Atenuador / Ganho Estático)
// ==========================================
template <typename T>
class GainNode : public NodeBase<T> {
private:
    int currentBlockSize = DSP2Config::DEFAULT_BLOCK_SIZE;
    T gain = static_cast<T>(1.0); // Parâmetro interno
public:
    GainNode() {
        this->input_buffers.resize(1, nullptr);
        this->output_buffers.resize(1, nullptr);
    }
    
    // Método para o Python ou outro nó alterar o valor
    void set_gain(T new_gain) { gain = new_gain; }

    void prepare(double /*sampleRate*/, int blockSize) override {
        currentBlockSize = blockSize;
        this->output_buffers[0] = new T[blockSize];
    }
    void process() override {
        const T* __restrict in = this->input_buffers[0];
        T* __restrict out = this->output_buffers[0];

        if (!in) {
            DSP2_LOG_ERROR("GainNode: Buffer de entrada ausente.");
            return;
        }

        for (int i = 0; i < currentBlockSize; ++i) {
            out[i] = in[i] * gain;
        }
    }
    ~GainNode() { delete[] this->output_buffers[0]; }
};

// ==========================================
// 4. ConstantNode (Gerador de DC / Offset)
// ==========================================
template <typename T>
class ConstantNode : public NodeBase<T> {
private:
    int currentBlockSize = DSP2Config::DEFAULT_BLOCK_SIZE;
    T value = static_cast<T>(0.0);
public:
    ConstantNode() {
        // Nenhuma entrada necessária
        this->input_buffers.resize(0); 
        this->output_buffers.resize(1, nullptr);
    }

    void set_value(T v) { value = v; }

    void prepare(double /*sampleRate*/, int blockSize) override {
        currentBlockSize = blockSize;
        this->output_buffers[0] = new T[blockSize];
    }
    void process() override {
        T* __restrict out = this->output_buffers[0];
        for (int i = 0; i < currentBlockSize; ++i) {
            out[i] = value;
        }
    }
    ~ConstantNode() { delete[] this->output_buffers[0]; }
};