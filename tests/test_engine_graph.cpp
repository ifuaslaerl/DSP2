#include <cmath>
#include <iostream>
#include <vector>

#include "../core/engine.hpp"

int main() {
    std::cout << "--- D(SP)^2 : Engine/Graph integration smoke test ---\n";

    const double sample_rate = 44100.0;
    const int block_size = 16;
    const double expected = 6.0;
    const double tolerance = 1e-9;

    Engine<double> engine;
    engine.set_signal_parameters(sample_rate, block_size);

    const int constant_id = engine.add_node("Constant");
    const int gain_id = engine.add_node("Gain");

    if (constant_id < 0 || gain_id < 0) {
        std::cout << "FAIL: Expected non-negative node ids.\n";
        return 1;
    }

    engine.set_node_parameter(constant_id, "value", 2.0);
    engine.set_node_parameter(gain_id, "gain", 3.0);
    engine.add_edge(constant_id, 0, gain_id, 0);

    engine.prepare_engine();
    engine.process_block();

    const std::vector<double> output = engine.get_node_output(gain_id, 0);
    if (static_cast<int>(output.size()) != block_size) {
        std::cout << "FAIL: Expected output size " << block_size
                  << ", got " << output.size() << ".\n";
        return 1;
    }

    for (int i = 0; i < block_size; ++i) {
        if (std::abs(output[i] - expected) > tolerance) {
            std::cout << "FAIL: Sample " << i << " expected " << expected
                      << ", got " << output[i] << ".\n";
            return 1;
        }
    }

    std::cout << "SUCCESS: Constant -> Gain produced the expected block.\n";
    return 0;
}
