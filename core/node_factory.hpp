#pragma once
#include <string>
#include <unordered_map>
#include <functional>
#include "node_base.hpp"
#include "logger.hpp"

/**
 * @brief Factory para criação dinâmica de nós (Phase 3.3).
 * Utilizado APENAS na fase de Setup. Não afeta a performance RT.
 */
template <typename T>
class NodeFactory {
public:
    using CreatorFunc = std::function<NodeBase<T>*()>;

    static NodeFactory& get_instance() {
        static NodeFactory instance;
        return instance;
    }

    // Registra uma classe no catálogo do motor
    void register_node(const std::string& name, CreatorFunc creator) {
        creators[name] = creator;
    }

    // Instancia um nó pelo nome da String vinda do Python/JSON
    NodeBase<T>* create(const std::string& name) {
        auto it = creators.find(name);
        if (it != creators.end()) {
            return it->second(); // Invoca o construtor apropriado
        }
        return nullptr;
    }

private:
    std::unordered_map<std::string, CreatorFunc> creators;
    NodeFactory() = default; // Singleton
};