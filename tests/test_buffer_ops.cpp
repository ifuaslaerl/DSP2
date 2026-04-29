#include <iostream>
#include <cmath>
#include "../core/buffer_ops.hpp"

int main() {
    std::cout << "--- D(SP)^2 : Iniciando Teste da Fase 2.2 (Buffer Ops e SIMD) ---\n";

    const int blockSize = 256;
    
    // Alocamos memórias (simulando a fase prepare)
    float* bufferA = new float[blockSize];
    float* bufferB = new float[blockSize];

    // 1. Teste de Clear e Preenchimento Básico
    DSP2BufferOps::clear(bufferA, blockSize);
    for(int i=0; i<blockSize; i++) bufferB[i] = 1.0f; // Sinal DC de 1.0

    // 2. Teste de Soma (Mixagem)
    // Somamos B em A. O buffer A que era 0.0 deve virar 1.0.
    DSP2BufferOps::add(bufferA, bufferB, blockSize);

    // 3. Teste Multiplicação Escalar (Ganho)
    // Aplicamos ganho de 5.0 no buffer A.
    DSP2BufferOps::multiply_scalar(bufferA, 5.0f, blockSize);

    // 4. Teste Multiplicação de Buffers (Modulação)
    // Multiplicamos A (que está em 5.0) por B (que está em 1.0)
    // Resultado em A deve continuar sendo 5.0 (5.0 * 1.0 = 5.0)
    DSP2BufferOps::multiply(bufferA, bufferB, blockSize);

    // 5. Validação
    bool success = true;
    for(int i=0; i < blockSize; ++i) {
        if (std::abs(bufferA[i] - 5.0f) > 1e-6) {
            success = false;
            break;
        }
    }

    delete[] bufferA;
    delete[] bufferB;

    if (success) {
        std::cout << "✅ SUCESSO: Operações de buffer (SIMD-ready) executadas perfeitamente.\n";
        return 0;
    } else {
        std::cout << "❌ FALHA: Erro na matemática dos buffers.\n";
        return 1;
    }
}