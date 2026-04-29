cmake_minimum_required(VERSION 3.15)
project(DSP2 VERSION 1.0.0 LANGUAGES CXX)

# Otimizações para processamento de sinais e C++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ==========================================
# Opções de Configuração do Build
# ==========================================
set(DSP2_TARGET "SIMULATION" CACHE STRING "Alvo de compilação: SIMULATION ou EMBEDDED")
message(STATUS "A compilar D(SP)^2 para o alvo: ${DSP2_TARGET}")

# ==========================================
# 1. Core DSP (A Biblioteca principal)
# ==========================================
# Aqui geramos o libdsp2_core.a estático que será o produto final embarcável
add_library(dsp2_core STATIC
    core/engine.cpp
    core/graph.cpp
    # À medida que os nós C++ forem criados, adicione-os aqui:
    # nodes_cpp/meu_no_matematico.cpp
)

# Exporta os cabeçalhos para quem for usar a biblioteca
target_include_directories(dsp2_core PUBLIC 
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
)

# Otimizações de performance em tempo real
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(dsp2_core PRIVATE -O3 -ffast-math -Wall -Wextra)
endif()

# ==========================================
# 2. Compilação Condicional (Simulação vs Embarcado)
# ==========================================
if(DSP2_TARGET STREQUAL "SIMULATION")
    message(STATUS "A configurar ambiente de Simulação com Bindings Python...")
    
    # Procura o pybind11 (certifique-se de o adicionar ao Dockerfile)
    find_package(pybind11 REQUIRED)

    # Cria o módulo Python a partir da pasta bindings/
    pybind11_add_module(dsp2_bindings bindings/bind_python.cpp)
    target_link_libraries(dsp2_bindings PRIVATE dsp2_core)
    
    # Coloca o ficheiro .so final na pasta dsp2/ DENTRO do diretório de build
    set_target_properties(dsp2_bindings PROPERTIES 
        OUTPUT_NAME "_dsp2_core" 
        LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/dsp2
    )

elseif(DSP2_TARGET STREQUAL "EMBEDDED")
    message(STATUS "A configurar ambiente Embarcado (Apenas Biblioteca Core)...")
    
    # Desativa exceções e RTTI para otimização crítica de memória/CPU em microcontroladores
    if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
        target_compile_options(dsp2_core PRIVATE -fno-exceptions -fno-rtti)
    endif()
    
    # Define uma macro para o código C++ saber que estamos em modo de embarque (modo mínimo)
    target_compile_definitions(dsp2_core PRIVATE DSP2_EMBEDDED_MODE)

    # No modo embarcado, ignoramos completamente a pasta bindings/ e o Python.
    # O build vai simplesmente gerar o 'libdsp2_core.a' na pasta de build.
endif()

# ==========================================
# 3. Testes Unitários e Validação (CTest)
# ==========================================
# Ativa o suporte nativo a testes do CMake
enable_testing()

# Compila o executável do teste da Fase 1
add_executable(test_phase1 tests/test_phase1.cpp)
target_link_libraries(test_phase1 PRIVATE dsp2_core)

# Regista o teste no CTest
add_test(NAME Phase1_CoreDataflow_Test COMMAND test_phase1)

message(STATUS "Testes configurados. Execute 'make test' apos compilar para rodar a validacao.")