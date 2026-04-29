#include <iostream>
#include <cmath>
#include "../core/engine.hpp"
#include "../nodes_cpp/lut_oscillator.hpp"

// ========================================================
// MÓDULO DE TESTE: Receptor para ler o buffer via Zero-Copy
// ========================================================
template <typename T>
class DummyReceiver : public NodeBase<T> {
public:
    T sample_zero;
    T sample_one;

    DummyReceiver() {
        this->input_buffers.resize(1, nullptr); // 1 Entrada
    }

    void prepare(double sampleRate, int blockSize) override {
        // Não aloca saída, pois é apenas um "ralo" (sink) de dados
    }

    void process() override {
        // Mapeamento Zero-Copy: input_buffers aponta para a memória do oscilador
        const T* in = this->input_buffers[0]; 
        
        // Vamos capturar as duas primeiras amostras para validar a onda
        sample_zero = in[0];
        sample_one = in[1];
    }
};

// ========================================================
// ROTINA DE TESTE (MAIN)
// ========================================================
int main() {
    std::cout << "--- D(SP)^2 : Iniciando Teste da Fase 2 (LUT Oscillator) ---\n";

    // 1. Instanciar o Grafo para modo EMBEDDED (float)
    Graph<float> graph;
    
    // 2. Instanciar os nós 
    // Frequência arbitrária de 441Hz. A 44100Hz de Sample Rate, 
    // 1 ciclo tem exatamente 100 samples.
    auto* osc = new LutOscillator<float>(441.0f);     
    auto* receiver = new DummyReceiver<float>();   

    graph.add_node(osc);
    graph.add_node(receiver);

    // 3. Ligar Saída 0 do oscilador à Entrada 0 do receptor
    graph.add_edge(0, 0, 1, 0);

    // 4. Compilar (Aloca memórias, gera a LUT e resolve Zero-Copy)
    std::cout << "[INFO] Compilando o Grafo...\n";
    graph.compile(44100.0, 256);

    // 5. Ciclo de Áudio (Lock-free e Allocation-free)
    std::cout << "[INFO] Processando bloco de audio...\n";
    graph.process();

    // 6. Validação
    // A fase inicial é 0, logo o sin(0) deve ser 0.
    // O próximo ponto (sample_one) deve ser um valor positivo da senoide em subida.
    float val_zero = receiver->sample_zero;
    float val_one = receiver->sample_one;
    
    delete osc;
    delete receiver;

    // Margem de erro pequena para o float
    if (std::abs(val_zero) < 1e-6 && val_one > 0.0f) {
        std::cout << "✅ SUCESSO: LutOscillator operando em O(1) e gerando curva corretamente.\n";
        return 0; // Código 0 = Sucesso para o CTest
    } else {
        std::cout << "❌ FALHA: Valores inesperados na onda gerada. Obtido [0]: " << val_zero << " e [1]: " << val_one << "\n";
        return 1; // Código 1 = Falha para o CTest
    }
}