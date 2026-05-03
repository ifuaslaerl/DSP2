#include <cmath>
#include <iostream>
#include <vector>

#include "../core/engine.hpp"
#include "../core/graph.hpp"
#include "../core/node_base.hpp"

namespace {

constexpr double kTolerance = 1e-9;

bool nearly_equal(double a, double b, double tolerance = kTolerance) {
    return std::abs(a - b) <= tolerance;
}

bool expect_true(bool condition, const char* message) {
    if (!condition) {
        std::cout << "FAIL: " << message << "\n";
        return false;
    }
    return true;
}

bool expect_block_value(const std::vector<double>& output, int expected_size, double expected_value) {
    if (static_cast<int>(output.size()) != expected_size) {
        std::cout << "FAIL: Expected output size " << expected_size
                  << ", got " << output.size() << ".\n";
        return false;
    }

    for (int i = 0; i < expected_size; ++i) {
        if (!nearly_equal(output[i], expected_value)) {
            std::cout << "FAIL: Sample " << i << " expected " << expected_value
                      << ", got " << output[i] << ".\n";
            return false;
        }
    }
    return true;
}

class InspectableSource final : public NodeBase<double> {
public:
    explicit InspectableSource(double value) : value_(value) {
        output_buffers.resize(1, nullptr);
        output_block_sizes.resize(1, 0);
        output_sample_rates.resize(1, 0.0);
    }

    void compute_dimensions() override {}

    void prepare() override {
        output_buffers[0] = new double[output_block_sizes[0]];
    }

    void process() override {
        for (int i = 0; i < output_block_sizes[0]; ++i) {
            output_buffers[0][i] = value_;
        }
    }

    const double* output_ptr() const {
        return output_buffers[0];
    }

    ~InspectableSource() override {
        delete[] output_buffers[0];
    }

private:
    double value_;
};

class InspectableSink final : public NodeBase<double> {
public:
    InspectableSink() {
        input_buffers.resize(1, nullptr);
        output_buffers.resize(1, nullptr);
        input_block_sizes.resize(1, 0);
        output_block_sizes.resize(1, 0);
        input_sample_rates.resize(1, 0.0);
        output_sample_rates.resize(1, 0.0);
    }

    void compute_dimensions() override {
        output_block_sizes[0] = input_block_sizes[0];
        output_sample_rates[0] = input_sample_rates[0];
    }

    void prepare() override {
        output_buffers[0] = new double[output_block_sizes[0]];
    }

    void process() override {
        if (!input_buffers[0]) {
            return;
        }
        for (int i = 0; i < output_block_sizes[0]; ++i) {
            output_buffers[0][i] = input_buffers[0][i];
        }
    }

    const double* input_ptr() const {
        return input_buffers[0];
    }

    ~InspectableSink() override {
        delete[] output_buffers[0];
    }
};

class DestructionProbeNode final : public NodeBase<double> {
public:
    explicit DestructionProbeNode(int* destruction_count)
        : destruction_count_(destruction_count) {
        output_buffers.resize(1, nullptr);
        output_block_sizes.resize(1, 0);
        output_sample_rates.resize(1, 0.0);
    }

    void compute_dimensions() override {}

    void prepare() override {}

    void process() override {}

    ~DestructionProbeNode() override {
        if (destruction_count_) {
            ++(*destruction_count_);
        }
    }

private:
    int* destruction_count_;
};

bool test_zero_copy_routing() {
    Graph<double> graph;
    auto* source = new InspectableSource(5.0);
    auto* sink = new InspectableSink();

    graph.add_node(source);
    graph.add_node(sink);
    graph.add_edge(0, 0, 1, 0);
    graph.compile(44100.0, 16);

    if (!expect_true(source->output_ptr() != nullptr, "Source output buffer must be allocated.")) {
        return false;
    }
    if (!expect_true(sink->input_ptr() == source->output_ptr(),
                     "Sink input pointer must alias source output buffer.")) {
        return false;
    }

    graph.process();
    const double* output = graph.get_node_output_buffer(1, 0);
    if (!expect_true(output != nullptr, "Sink output buffer must be readable.")) {
        return false;
    }

    for (int i = 0; i < 16; ++i) {
        if (!nearly_equal(output[i], 5.0)) {
            std::cout << "FAIL: Zero-copy routed sample " << i << " expected 5, got "
                      << output[i] << ".\n";
            return false;
        }
    }

    return true;
}

bool test_graph_destroys_owned_nodes() {
    int destruction_count = 0;

    {
        Graph<double> graph;
        graph.add_node(new DestructionProbeNode(&destruction_count));
        graph.add_node(new DestructionProbeNode(&destruction_count));
    }

    return expect_true(destruction_count == 2,
                       "Graph destructor must destroy nodes passed to add_node().");
}

bool test_topological_order() {
    Engine<double> engine;
    engine.set_signal_parameters(44100.0, 16);

    const int source = engine.add_node("Constant");
    const int gain_a = engine.add_node("Gain");
    const int gain_b = engine.add_node("Gain");

    if (!expect_true(source >= 0 && gain_a >= 0 && gain_b >= 0,
                     "Topological test nodes must be created.")) {
        return false;
    }

    engine.set_node_parameter(source, "value", 2.0);
    engine.set_node_parameter(gain_a, "gain", 3.0);
    engine.set_node_parameter(gain_b, "gain", 4.0);
    engine.add_edge(source, 0, gain_a, 0);
    engine.add_edge(gain_a, 0, gain_b, 0);

    engine.prepare_engine();
    engine.process_block();

    return expect_block_value(engine.get_node_output(gain_b, 0), 16, 24.0);
}

bool test_multiple_inputs() {
    Engine<double> engine;
    engine.set_signal_parameters(44100.0, 16);

    const int left = engine.add_node("Constant");
    const int right = engine.add_node("Constant");
    const int add = engine.add_node("Add");

    if (!expect_true(left >= 0 && right >= 0 && add >= 0,
                     "Multiple input test nodes must be created.")) {
        return false;
    }

    engine.set_node_parameter(left, "value", 2.0);
    engine.set_node_parameter(right, "value", 4.0);
    engine.add_edge(left, 0, add, 0);
    engine.add_edge(right, 0, add, 1);

    engine.prepare_engine();
    engine.process_block();

    return expect_block_value(engine.get_node_output(add, 0), 16, 6.0);
}

bool test_fan_out_routing() {
    Engine<double> engine;
    engine.set_signal_parameters(44100.0, 16);

    const int source = engine.add_node("Constant");
    const int gain_a = engine.add_node("Gain");
    const int gain_b = engine.add_node("Gain");

    if (!expect_true(source >= 0 && gain_a >= 0 && gain_b >= 0,
                     "Fan-out test nodes must be created.")) {
        return false;
    }

    engine.set_node_parameter(source, "value", 2.0);
    engine.set_node_parameter(gain_a, "gain", 3.0);
    engine.set_node_parameter(gain_b, "gain", 5.0);
    engine.add_edge(source, 0, gain_a, 0);
    engine.add_edge(source, 0, gain_b, 0);

    engine.prepare_engine();
    engine.process_block();

    if (!expect_block_value(engine.get_node_output(gain_a, 0), 16, 6.0)) {
        return false;
    }
    return expect_block_value(engine.get_node_output(gain_b, 0), 16, 10.0);
}

bool test_multi_layer_routing() {
    Engine<double> engine;
    engine.set_signal_parameters(44100.0, 16);

    const int source = engine.add_node("Constant");
    const int gain_a = engine.add_node("Gain");
    const int gain_b = engine.add_node("Gain");
    const int offset = engine.add_node("Constant");
    const int add = engine.add_node("Add");

    if (!expect_true(source >= 0 && gain_a >= 0 && gain_b >= 0 && offset >= 0 && add >= 0,
                     "Multi-layer test nodes must be created.")) {
        return false;
    }

    engine.set_node_parameter(source, "value", 2.0);
    engine.set_node_parameter(gain_a, "gain", 3.0);
    engine.set_node_parameter(gain_b, "gain", 4.0);
    engine.set_node_parameter(offset, "value", 1.0);
    engine.add_edge(source, 0, gain_a, 0);
    engine.add_edge(gain_a, 0, gain_b, 0);
    engine.add_edge(gain_b, 0, add, 0);
    engine.add_edge(offset, 0, add, 1);

    engine.prepare_engine();
    engine.process_block();

    return expect_block_value(engine.get_node_output(add, 0), 16, 25.0);
}

bool test_invalid_ids_and_ports() {
    Engine<double> engine;
    engine.set_signal_parameters(44100.0, 16);

    if (!expect_true(engine.add_node("NoSuchNode") == -1,
                     "Unknown node type must return -1.")) {
        return false;
    }

    const int constant = engine.add_node("Constant");
    if (!expect_true(constant >= 0, "Constant node must be created.")) {
        return false;
    }

    engine.prepare_engine();
    engine.process_block();

    if (!expect_true(engine.get_node_output(-1, 0).empty(),
                     "Negative node output request must return an empty vector.")) {
        return false;
    }
    if (!expect_true(engine.get_node_output(constant, 9).empty(),
                     "Invalid port output request must return an empty vector.")) {
        return false;
    }
    if (!expect_true(nearly_equal(engine.get_node_output_sample_rate(-1, 0), 0.0),
                     "Negative node sample rate request must return 0.")) {
        return false;
    }
    if (!expect_true(nearly_equal(engine.get_node_output_sample_rate(constant, 9), 0.0),
                     "Invalid port sample rate request must return 0.")) {
        return false;
    }

    return true;
}

bool test_dimension_propagation() {
    Engine<double> engine;
    engine.set_signal_parameters(48000.0, 32);

    const int constant = engine.add_node("Constant");
    const int gain = engine.add_node("Gain");

    if (!expect_true(constant >= 0 && gain >= 0,
                     "Dimension propagation nodes must be created.")) {
        return false;
    }

    engine.set_node_parameter(constant, "value", 1.0);
    engine.set_node_parameter(gain, "gain", 2.0);
    engine.add_edge(constant, 0, gain, 0);
    engine.prepare_engine();
    engine.process_block();

    if (!expect_true(static_cast<int>(engine.get_node_output(gain, 0).size()) == 32,
                     "Block size must propagate to routed output.")) {
        return false;
    }
    if (!expect_true(nearly_equal(engine.get_node_output_sample_rate(gain, 0), 48000.0),
                     "Sample rate must propagate to routed output.")) {
        return false;
    }

    return true;
}

}  // namespace

int main() {
    std::cout << "--- D(SP)^2 : Graph routing test suite ---\n";

    if (!test_zero_copy_routing()) return 1;
    if (!test_graph_destroys_owned_nodes()) return 1;
    if (!test_topological_order()) return 1;
    if (!test_multiple_inputs()) return 1;
    if (!test_fan_out_routing()) return 1;
    if (!test_multi_layer_routing()) return 1;
    if (!test_invalid_ids_and_ports()) return 1;
    if (!test_dimension_propagation()) return 1;

    std::cout << "SUCCESS: Graph routing scenarios passed.\n";
    return 0;
}
