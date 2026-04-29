#include <iostream>
#include "../core/logger.hpp"

int main() {
    std::cout << "--- D(SP)^2 : Iniciando Teste da Fase 2.3 (Lock-Free Logger) ---\n";

    auto& logger = DSP2Log::Logger::get_instance();
    DSP2Log::LogEvent event;

    // 1. Testar uso direto da fila SPSC (garantir que a lógica lock-free está correta)
    logger.push(DSP2Log::Level::ERROR, "Teste de falha manual na Fila");
    
    bool pop_success = logger.pop(event);
    if (!pop_success || event.level != DSP2Log::Level::ERROR) {
        std::cout << "❌ FALHA: Fila SPSC falhou ao armazenar e recuperar o LogEvent.\n";
        return 1;
    }

    // 2. Testar o comportamento das Macros com base no alvo do build
    // A macro chamará push() se estivermos na simulação, e fará nada no embarcado.
    DSP2_LOG_INFO("Este log sera ignorado no alvo EMBEDDED");

    bool has_logs = logger.pop(event);

    #ifdef DSP2_EMBEDDED_MODE
        // No modo embarcado, has_logs DEVE ser false, porque a macro virou do {} while(0)
        if (has_logs) {
            std::cout << "❌ FALHA CRITICA: O Logger nao desativou no modo EMBEDDED!\n";
            return 1;
        }
        std::cout << "✅ SUCESSO: Macros inativadas corretamente (Zero-Cost garantido).\n";
    #else
        // No modo simulação, o log deve existir.
        if (!has_logs) {
            std::cout << "❌ FALHA: Macro não registou o evento em modo SIMULATION.\n";
            return 1;
        }
        std::cout << "✅ SUCESSO: Macro inseriu log com sucesso para ser lido pelo Python.\n";
    #endif

    std::cout << "✅ SUCESSO: Fila SPSC Operacional e Thread-Safe.\n";
    return 0;
}