#pragma once

#include <atomic>
#include <array>

namespace DSP2Log {
    
    // Níveis de severidade
    enum class Level { INFO, ERROR };

    // Estrutura do evento (Tamanho fixo, sem std::string)
    struct LogEvent {
        Level level;
        const char* message; // Aceita apenas strings literais na fase de processo
    };

    // Tamanho do Ring Buffer (potência de 2 é ideal)
    constexpr size_t RING_BUFFER_SIZE = 1024;

    /**
     * @brief Logger SPSC (Single-Producer, Single-Consumer) Lock-Free.
     * Seguro para uso em threads de áudio de tempo real.
     */
    class Logger {
    private:
        std::array<LogEvent, RING_BUFFER_SIZE> buffer;
        std::atomic<size_t> write_index{0};
        std::atomic<size_t> read_index{0};

        // Construtor privado (Singleton)
        Logger() = default;

    public:
        // Acesso à instância global
        static Logger& get_instance() {
            static Logger instance;
            return instance;
        }

        // ==========================================
        // PRODUTOR (Chamado pela Thread de Áudio / C++)
        // ==========================================
        void push(Level level, const char* msg) {
            // memory_order_relaxed: Lê a nossa própria escrita sem sincronização pesada
            size_t current_write = write_index.load(std::memory_order_relaxed);
            size_t next_write = (current_write + 1) % RING_BUFFER_SIZE;

            // Se o buffer não estiver cheio
            if (next_write != read_index.load(std::memory_order_acquire)) {
                buffer[current_write] = {level, msg};
                // Atualiza o índice para o consumidor ver
                write_index.store(next_write, std::memory_order_release);
            }
            // Se estiver cheio, o log é descartado (comportamento padrão RT para não bloquear)
        }

        // ==========================================
        // CONSUMIDOR (Chamado pela Thread do Python via Pybind11)
        // ==========================================
        bool pop(LogEvent& event) {
            size_t current_read = read_index.load(std::memory_order_relaxed);
            
            // Se estiver vazio
            if (current_read == write_index.load(std::memory_order_acquire)) {
                return false; 
            }

            // Copia o evento e avança
            event = buffer[current_read];
            read_index.store((current_read + 1) % RING_BUFFER_SIZE, std::memory_order_release);
            return true;
        }
    };
}

// ==========================================
// MACROS DE ACESSO (Zero-Cost em EMBEDDED)
// ==========================================

#ifndef DSP2_EMBEDDED_MODE
    // Em modo SIMULAÇÃO, injeta os logs no Ring Buffer
    #define DSP2_LOG_INFO(msg)  DSP2Log::Logger::get_instance().push(DSP2Log::Level::INFO, msg)
    #define DSP2_LOG_ERROR(msg) DSP2Log::Logger::get_instance().push(DSP2Log::Level::ERROR, msg)
#else
    // Em modo EMBARCADO, as macros são removidas pelo pré-processador (Custo zero de CPU e Memória)
    #define DSP2_LOG_INFO(msg)  do {} while(0)
    #define DSP2_LOG_ERROR(msg) do {} while(0)
#endif