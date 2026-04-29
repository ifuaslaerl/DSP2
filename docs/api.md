# D(SP)^2 - Core DSP API Reference

Este documento lista as funções, utilitários matemáticos e classes base disponíveis no `core/` do D(SP)^2. 
**Nota para Agentes de IA:** Sempre consulte esta lista antes de implementar matemática customizada em um novo nó para reaproveitar código otimizado.

## 1. Operações de Buffer (SIMD Otimizadas)
Funções para manipular blocos inteiros de áudio de forma rápida.

## 2. Aproximações Matemáticas Rápidas (Fast Math)
Funções trigonométricas e logarítmicas que trocam precisão absoluta por velocidade extrema.

**Regra Estrita de Hardware:** Funções da biblioteca `<cmath>` são lentas em microcontroladores sem FPU ou causam gargalos de ciclos. Todo o cálculo matemático nos nós `nodes_cpp/` DEVE consumir as tabelas de pesquisa (Lookup Tables - LUTs) ou aproximações de Taylor listadas abaixo.

### `DSP2FastMath::SineLUT<T>`
- **Assinatura:** `inline T get_value(T phase_index) const`
- **Descrição:** Tabela de pesquisa pré-calculada para geração de senoide.
- **Configuração:** O tamanho padrão é definido pela constante `DSP2Config::SINE_LUT_DEFAULT_SIZE` em `core/constants.hpp`.
- **Notas de Performance:** Implementação $O(1)$ sem chamadas de `std::sin` no loop de áudio. Utiliza `DSP2Config::PI` (calculado via `std::acos(-1)`) para a geração inicial da tabela.