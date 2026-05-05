#include <cmath>
#include <iostream>
#include <vector>

#include "../core/engine.hpp"
#include "../core/fft.hpp"
#include "../core/graph.hpp"
#include "../core/node_base.hpp"
#include "../nodes_cpp/butterworth_filter.hpp"
#include "../nodes_cpp/audio_file_input.hpp"
#include "../nodes_cpp/convolution.hpp"
#include "../nodes_cpp/decimator.hpp"
#include "../nodes_cpp/math_nodes.hpp"
#include "../nodes_cpp/noise_generator.hpp"
#include "../nodes_cpp/quadrature_modulator.hpp"
#include "../nodes_cpp/spectrum_analyser.hpp"
#include "../nodes_cpp/spectral_peak_picker.hpp"
#include "../nodes_cpp/windowing.hpp"

namespace {

constexpr double kTolerance = 1e-9;
constexpr double kLooseTolerance = 1e-6;
constexpr double kPi = 3.14159265358979323846;

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

bool expect_block_value(const std::vector<double>& output, int expected_size, double expected_value,
                        double tolerance = kTolerance) {
    if (static_cast<int>(output.size()) != expected_size) {
        std::cout << "FAIL: Expected output size " << expected_size
                  << ", got " << output.size() << ".\n";
        return false;
    }

    for (int i = 0; i < expected_size; ++i) {
        if (!nearly_equal(output[i], expected_value, tolerance)) {
            std::cout << "FAIL: Sample " << i << " expected " << expected_value
                      << ", got " << output[i] << ".\n";
            return false;
        }
    }
    return true;
}

class SequenceSource final : public NodeBase<double> {
public:
    SequenceSource() {
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
            output_buffers[0][i] = static_cast<double>(i);
        }
    }

    ~SequenceSource() override {
        delete[] output_buffers[0];
    }
};

class ConstantSource final : public NodeBase<double> {
public:
    explicit ConstantSource(double value) : value_(value) {
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

    ~ConstantSource() override {
        delete[] output_buffers[0];
    }

private:
    double value_;
};

class SpectrumFrameSource final : public NodeBase<double> {
public:
    SpectrumFrameSource(const std::vector<double>& powers, const std::vector<double>& frequencies)
        : powers_(powers), frequencies_(frequencies) {
        output_buffers.resize(2, nullptr);
        output_block_sizes.resize(2, 0);
        output_sample_rates.resize(2, 0.0);
    }

    void compute_dimensions() override {
        output_block_sizes[0] = static_cast<int>(powers_.size());
        output_block_sizes[1] = static_cast<int>(frequencies_.size());
    }

    void prepare() override {
        output_buffers[0] = new double[output_block_sizes[0]];
        output_buffers[1] = new double[output_block_sizes[1]];
    }

    void process() override {
        for (int i = 0; i < output_block_sizes[0]; ++i) {
            output_buffers[0][i] = powers_[static_cast<size_t>(i)];
        }
        for (int i = 0; i < output_block_sizes[1]; ++i) {
            output_buffers[1][i] = frequencies_[static_cast<size_t>(i)];
        }
    }

    ~SpectrumFrameSource() override {
        delete[] output_buffers[0];
        delete[] output_buffers[1];
    }

private:
    std::vector<double> powers_;
    std::vector<double> frequencies_;
};

bool test_constant_node() {
    Engine<double> engine;
    engine.set_signal_parameters(44100.0, 8);
    const int node = engine.add_node("Constant");
    if (!expect_true(node >= 0, "Constant node must be created.")) return false;

    engine.set_node_parameter(node, "value", 7.5);
    engine.prepare_engine();
    engine.process_block();

    return expect_block_value(engine.get_node_output(node, 0), 8, 7.5);
}

bool test_gain_node() {
    Engine<double> engine;
    engine.set_signal_parameters(44100.0, 8);
    const int source = engine.add_node("Constant");
    const int gain = engine.add_node("Gain");
    if (!expect_true(source >= 0 && gain >= 0, "Gain test nodes must be created.")) return false;

    engine.set_node_parameter(source, "value", 2.0);
    engine.set_node_parameter(gain, "gain", 3.0);
    engine.add_edge(source, 0, gain, 0);
    engine.prepare_engine();
    engine.process_block();

    return expect_block_value(engine.get_node_output(gain, 0), 8, 6.0);
}

bool test_add_node() {
    Engine<double> engine;
    engine.set_signal_parameters(44100.0, 8);
    const int left = engine.add_node("Constant");
    const int right = engine.add_node("Constant");
    const int add = engine.add_node("Add");
    if (!expect_true(left >= 0 && right >= 0 && add >= 0, "Add test nodes must be created.")) {
        return false;
    }

    engine.set_node_parameter(left, "value", 2.0);
    engine.set_node_parameter(right, "value", 4.0);
    engine.add_edge(left, 0, add, 0);
    engine.add_edge(right, 0, add, 1);
    engine.prepare_engine();
    engine.process_block();

    return expect_block_value(engine.get_node_output(add, 0), 8, 6.0);
}

bool test_multiply_node() {
    Engine<double> engine;
    engine.set_signal_parameters(44100.0, 8);
    const int left = engine.add_node("Constant");
    const int right = engine.add_node("Constant");
    const int multiply = engine.add_node("Multiply");
    if (!expect_true(left >= 0 && right >= 0 && multiply >= 0,
                     "Multiply test nodes must be created.")) {
        return false;
    }

    engine.set_node_parameter(left, "value", 2.5);
    engine.set_node_parameter(right, "value", 4.0);
    engine.add_edge(left, 0, multiply, 0);
    engine.add_edge(right, 0, multiply, 1);
    engine.prepare_engine();
    engine.process_block();

    return expect_block_value(engine.get_node_output(multiply, 0), 8, 10.0);
}

bool test_sine_oscillator_node() {
    Engine<double> engine;
    engine.set_signal_parameters(44100.0, 8);
    const int oscillator = engine.add_node("SineOscillator");
    if (!expect_true(oscillator >= 0, "SineOscillator node must be created.")) return false;

    engine.set_node_parameter(oscillator, "frequency", 0.0);
    engine.prepare_engine();
    engine.process_block();

    return expect_block_value(engine.get_node_output(oscillator, 0), 8, 0.0, kLooseTolerance);
}

bool test_sine_oscillator_continuity() {
    Engine<double> engine;
    engine.set_signal_parameters(44100.0, 8);
    const int oscillator = engine.add_node("SineOscillator");
    if (!expect_true(oscillator >= 0, "SineOscillator continuity node must be created.")) {
        return false;
    }

    engine.set_node_parameter(oscillator, "frequency", 440.0);
    engine.prepare_engine();
    engine.process_block();
    const std::vector<double> first = engine.get_node_output(oscillator, 0);
    engine.process_block();
    const std::vector<double> second = engine.get_node_output(oscillator, 0);

    if (!expect_true(static_cast<int>(first.size()) == 8 && static_cast<int>(second.size()) == 8,
                     "SineOscillator continuity outputs must preserve block size.")) {
        return false;
    }

    for (int i = 0; i < 8; ++i) {
        if (!std::isfinite(first[i]) || !std::isfinite(second[i])) {
            std::cout << "FAIL: SineOscillator sample " << i << " is not finite.\n";
            return false;
        }
        if (std::abs(first[i]) > 1.0 + kLooseTolerance ||
            std::abs(second[i]) > 1.0 + kLooseTolerance) {
            std::cout << "FAIL: SineOscillator sample " << i << " is outside [-1, 1].\n";
            return false;
        }
    }

    if (!expect_true(!nearly_equal(second[0], 0.0, 1e-3),
                     "SineOscillator phase must continue across blocks.")) {
        return false;
    }

    return true;
}

bool test_noise_generator_node() {
    Engine<double> engine;
    engine.set_signal_parameters(44100.0, 16);
    const int noise = engine.add_node("NoiseGenerator");
    if (!expect_true(noise >= 0, "NoiseGenerator node must be created.")) return false;

    engine.set_node_parameter(noise, "amplitude", 0.5);
    engine.set_node_parameter(noise, "seed", 12345.0);
    engine.prepare_engine();
    engine.process_block();

    const std::vector<double> output = engine.get_node_output(noise, 0);
    if (!expect_true(static_cast<int>(output.size()) == 16,
                     "NoiseGenerator output must preserve block size.")) {
        return false;
    }

    bool differs_from_first = false;
    for (int i = 0; i < 16; ++i) {
        if (output[i] < -0.5 || output[i] > 0.5) {
            std::cout << "FAIL: NoiseGenerator sample " << i
                      << " is outside configured amplitude.\n";
            return false;
        }
        if (!nearly_equal(output[i], output[0])) {
            differs_from_first = true;
        }
    }

    return expect_true(differs_from_first, "NoiseGenerator output block must not be constant.");
}

bool test_noise_generator_same_seed_determinism() {
    Engine<double> first_engine;
    Engine<double> second_engine;
    first_engine.set_signal_parameters(44100.0, 16);
    second_engine.set_signal_parameters(44100.0, 16);

    const int first = first_engine.add_node("NoiseGenerator");
    const int second = second_engine.add_node("NoiseGenerator");
    if (!expect_true(first >= 0 && second >= 0,
                     "NoiseGenerator deterministic nodes must be created.")) {
        return false;
    }

    first_engine.set_node_parameter(first, "amplitude", 0.5);
    second_engine.set_node_parameter(second, "amplitude", 0.5);
    first_engine.set_node_parameter(first, "seed", 999.0);
    second_engine.set_node_parameter(second, "seed", 999.0);

    first_engine.prepare_engine();
    second_engine.prepare_engine();
    first_engine.process_block();
    second_engine.process_block();

    const std::vector<double> first_output = first_engine.get_node_output(first, 0);
    const std::vector<double> second_output = second_engine.get_node_output(second, 0);
    if (!expect_true(first_output.size() == second_output.size() &&
                     static_cast<int>(first_output.size()) == 16,
                     "NoiseGenerator deterministic outputs must have matching size.")) {
        return false;
    }

    for (int i = 0; i < 16; ++i) {
        if (!nearly_equal(first_output[i], second_output[i])) {
            std::cout << "FAIL: NoiseGenerator same seed sample " << i
                      << " differs between engines.\n";
            return false;
        }
    }

    return true;
}

bool test_noise_generator_different_seeds_diverge() {
    Engine<double> first_engine;
    Engine<double> second_engine;
    first_engine.set_signal_parameters(44100.0, 16);
    second_engine.set_signal_parameters(44100.0, 16);

    const int first = first_engine.add_node("NoiseGenerator");
    const int second = second_engine.add_node("NoiseGenerator");
    if (!expect_true(first >= 0 && second >= 0,
                     "NoiseGenerator different seed nodes must be created.")) {
        return false;
    }

    first_engine.set_node_parameter(first, "seed", 1001.0);
    second_engine.set_node_parameter(second, "seed", 2002.0);
    first_engine.prepare_engine();
    second_engine.prepare_engine();
    first_engine.process_block();
    second_engine.process_block();

    const std::vector<double> first_output = first_engine.get_node_output(first, 0);
    const std::vector<double> second_output = second_engine.get_node_output(second, 0);
    if (!expect_true(first_output.size() == second_output.size() &&
                     static_cast<int>(first_output.size()) == 16,
                     "NoiseGenerator different seed outputs must have matching size.")) {
        return false;
    }

    for (int i = 0; i < 16; ++i) {
        if (!nearly_equal(first_output[i], second_output[i])) {
            return true;
        }
    }

    return expect_true(false, "NoiseGenerator different seeds must produce different output.");
}

bool test_audio_file_input_node_streams_samples_and_pads_eof() {
    Engine<double> engine;
    engine.set_signal_parameters(44100.0, 4);
    const int audio = engine.add_node("AudioFileInput");
    if (!expect_true(audio >= 0, "AudioFileInput node must be created.")) return false;

    engine.set_node_parameter_array(audio, "samples", {0.25, -0.5, 0.75, -1.0, 0.5});
    engine.prepare_engine();

    engine.process_block();
    const std::vector<double> first = engine.get_node_output(audio, 0);
    if (!expect_true(static_cast<int>(first.size()) == 4,
                     "AudioFileInput first block must preserve block size.")) {
        return false;
    }

    const double expected_first[4] = {0.25, -0.5, 0.75, -1.0};
    for (int i = 0; i < 4; ++i) {
        if (!nearly_equal(first[i], expected_first[i])) {
            std::cout << "FAIL: AudioFileInput first block sample " << i
                      << " expected " << expected_first[i] << ", got " << first[i] << ".\n";
            return false;
        }
    }

    engine.process_block();
    const std::vector<double> second = engine.get_node_output(audio, 0);
    const double expected_second[4] = {0.5, 0.0, 0.0, 0.0};
    for (int i = 0; i < 4; ++i) {
        if (!nearly_equal(second[i], expected_second[i])) {
            std::cout << "FAIL: AudioFileInput second block sample " << i
                      << " expected " << expected_second[i] << ", got " << second[i] << ".\n";
            return false;
        }
    }

    return true;
}

bool test_real_fft_plan_impulse_response() {
    DSP2FFT::RealFFTPlan<double> plan;
    if (!expect_true(plan.configure(8), "RealFFTPlan must configure power-of-two size.")) {
        return false;
    }

    const double input[8] = {1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
    if (!expect_true(plan.execute(input, 8), "RealFFTPlan must execute impulse input.")) {
        return false;
    }

    for (int bin = 0; bin < 8; ++bin) {
        const double power = (plan.real(bin) * plan.real(bin)) + (plan.imag(bin) * plan.imag(bin));
        if (!nearly_equal(power, 1.0, kLooseTolerance)) {
            std::cout << "FAIL: FFT impulse bin " << bin << " expected power 1, got "
                      << power << ".\n";
            return false;
        }
    }

    return true;
}

bool test_spectrum_analyser_dimensions_and_frequencies() {
    Engine<double> engine;
    engine.set_signal_parameters(8000.0, 10);
    const int audio = engine.add_node("AudioFileInput");
    const int analyser = engine.add_node("SpectrumAnalyser");
    if (!expect_true(audio >= 0 && analyser >= 0,
                     "SpectrumAnalyser dimension test nodes must be created.")) {
        return false;
    }

    engine.set_node_parameter_array(audio, "samples", {1.0, 0.0, 0.0, 0.0, 0.0});
    engine.set_node_parameter(analyser, "fft_size", 16.0);
    engine.add_edge(audio, 0, analyser, 0);
    engine.prepare_engine();
    engine.process_block();

    if (!expect_true(engine.get_node_output_port_count(analyser) == 2,
                     "SpectrumAnalyser must expose power and frequency ports.")) {
        return false;
    }

    const std::vector<double> power = engine.get_node_output(analyser, 0);
    const std::vector<double> frequencies = engine.get_node_output(analyser, 1);
    if (!expect_true(static_cast<int>(power.size()) == 9 &&
                     static_cast<int>(frequencies.size()) == 9,
                     "SpectrumAnalyser must output fft_size/2 + 1 bins.")) {
        return false;
    }

    for (int bin = 0; bin < 9; ++bin) {
        const double expected_frequency = static_cast<double>(bin) * 8000.0 / 16.0;
        if (!nearly_equal(frequencies[bin], expected_frequency, kLooseTolerance)) {
            std::cout << "FAIL: Spectrum frequency bin " << bin << " expected "
                      << expected_frequency << ", got " << frequencies[bin] << ".\n";
            return false;
        }
    }

    return true;
}

bool test_spectrum_analyser_detects_aligned_sine_bin() {
    Engine<double> engine;
    engine.set_signal_parameters(16.0, 16);
    const int audio = engine.add_node("AudioFileInput");
    const int analyser = engine.add_node("SpectrumAnalyzer");
    if (!expect_true(audio >= 0 && analyser >= 0,
                     "SpectrumAnalyzer alias test nodes must be created.")) {
        return false;
    }

    std::vector<double> samples(16, 0.0);
    for (int i = 0; i < 16; ++i) {
        samples[static_cast<size_t>(i)] = std::sin(2.0 * kPi * 3.0 * static_cast<double>(i) / 16.0);
    }

    engine.set_node_parameter_array(audio, "samples", samples);
    engine.set_node_parameter(analyser, "fft_size", 16.0);
    engine.add_edge(audio, 0, analyser, 0);
    engine.prepare_engine();
    engine.process_block();

    const std::vector<double> power = engine.get_node_output(analyser, 0);
    if (!expect_true(static_cast<int>(power.size()) == 9,
                     "SpectrumAnalyzer alias output must expose one-sided bins.")) {
        return false;
    }

    int max_bin = 0;
    for (int bin = 1; bin < static_cast<int>(power.size()); ++bin) {
        if (power[bin] > power[max_bin]) {
            max_bin = bin;
        }
    }

    if (!expect_true(max_bin == 3, "SpectrumAnalyser must peak at the aligned sine bin.")) {
        std::cout << "FAIL: Spectrum max bin expected 3, got " << max_bin << ".\n";
        return false;
    }

    return expect_true(power[3] > 0.20, "Spectrum aligned sine bin must carry strong power.");
}

bool test_spectral_peak_picker_selects_strongest_local_peaks() {
    Graph<double> graph;
    auto* source = new SpectrumFrameSource(
        {0.0, 1.0, 5.0, 1.0, 0.0, 2.0, 8.0, 2.0, 0.0, 7.0, 1.0},
        {0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0}
    );
    auto* picker = new SpectralPeakPicker<double>();

    graph.add_node(source);
    graph.add_node(picker);
    graph.set_node_parameter(1, "peak_count", 3.0);
    graph.set_node_parameter(1, "min_frequency", 0.0);
    graph.add_edge(0, 0, 1, 0);
    graph.add_edge(0, 1, 1, 1);
    graph.compile(44100.0, 16);
    graph.process();

    if (!expect_true(graph.get_node_output_size(1, 0) == 3 &&
                     graph.get_node_output_size(1, 1) == 3,
                     "SpectralPeakPicker outputs must match peak_count.")) {
        return false;
    }

    const double* frequencies = graph.get_node_output_buffer(1, 0);
    const double* powers = graph.get_node_output_buffer(1, 1);
    if (!expect_true(frequencies != nullptr && powers != nullptr,
                     "SpectralPeakPicker outputs must be readable.")) {
        return false;
    }

    const double expected_frequencies[3] = {60.0, 90.0, 20.0};
    const double expected_powers[3] = {8.0, 7.0, 5.0};
    for (int i = 0; i < 3; ++i) {
        if (!nearly_equal(frequencies[i], expected_frequencies[i]) ||
            !nearly_equal(powers[i], expected_powers[i])) {
            std::cout << "FAIL: SpectralPeakPicker peak " << i << " expected ("
                      << expected_frequencies[i] << ", " << expected_powers[i]
                      << "), got (" << frequencies[i] << ", " << powers[i] << ").\n";
            return false;
        }
    }

    return true;
}

bool test_spectral_peak_picker_filters_and_pads() {
    Graph<double> graph;
    auto* source = new SpectrumFrameSource(
        {0.0, 9.0, 1.0, 8.0, 1.0, 7.0, 1.0},
        {0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0}
    );
    auto* picker = new SpectralPeakPicker<double>();

    graph.add_node(source);
    graph.add_node(picker);
    graph.set_node_parameter(1, "peak_count", 3.0);
    graph.set_node_parameter(1, "min_frequency", 20.0);
    graph.set_node_parameter(1, "max_frequency", 40.0);
    graph.set_node_parameter(1, "threshold", 5.0);
    graph.add_edge(0, 0, 1, 0);
    graph.add_edge(0, 1, 1, 1);
    graph.compile(44100.0, 16);
    graph.process();

    const double* frequencies = graph.get_node_output_buffer(1, 0);
    const double* powers = graph.get_node_output_buffer(1, 1);
    if (!expect_true(frequencies != nullptr && powers != nullptr,
                     "SpectralPeakPicker filtered outputs must be readable.")) {
        return false;
    }

    if (!nearly_equal(frequencies[0], 30.0) || !nearly_equal(powers[0], 8.0)) {
        std::cout << "FAIL: SpectralPeakPicker filter expected first peak (30, 8), got ("
                  << frequencies[0] << ", " << powers[0] << ").\n";
        return false;
    }

    for (int i = 1; i < 3; ++i) {
        if (!nearly_equal(frequencies[i], 0.0) || !nearly_equal(powers[i], 0.0)) {
            std::cout << "FAIL: SpectralPeakPicker filter expected zero padding at " << i
                      << ", got (" << frequencies[i] << ", " << powers[i] << ").\n";
            return false;
        }
    }

    return true;
}

bool test_spectral_peak_picker_min_bin_distance_replaces_weaker_neighbor() {
    Graph<double> graph;
    auto* source = new SpectrumFrameSource(
        {0.0, 1.0, 0.0, 1.0, 5.0, 1.0, 8.0, 1.0, 0.0, 1.0, 4.0, 1.0},
        {0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0, 110.0}
    );
    auto* picker = new SpectralPeakPicker<double>();

    graph.add_node(source);
    graph.add_node(picker);
    graph.set_node_parameter(1, "peak_count", 2.0);
    graph.set_node_parameter(1, "min_frequency", 0.0);
    graph.set_node_parameter(1, "min_bin_distance", 2.0);
    graph.add_edge(0, 0, 1, 0);
    graph.add_edge(0, 1, 1, 1);
    graph.compile(44100.0, 16);
    graph.process();

    const double* frequencies = graph.get_node_output_buffer(1, 0);
    const double* powers = graph.get_node_output_buffer(1, 1);
    if (!expect_true(frequencies != nullptr && powers != nullptr,
                     "SpectralPeakPicker distance outputs must be readable.")) {
        return false;
    }

    if (!nearly_equal(frequencies[0], 60.0) || !nearly_equal(powers[0], 8.0) ||
        !nearly_equal(frequencies[1], 100.0) || !nearly_equal(powers[1], 4.0)) {
        std::cout << "FAIL: SpectralPeakPicker distance expected (60, 8), (100, 4), got ("
                  << frequencies[0] << ", " << powers[0] << "), ("
                  << frequencies[1] << ", " << powers[1] << ").\n";
        return false;
    }

    return true;
}

bool test_decimator_node() {
    Graph<double> graph;
    auto* source = new SequenceSource();
    auto* decimator = new Decimator<double>();

    graph.add_node(source);
    graph.add_node(decimator);
    graph.set_node_parameter(1, "factor", 2.0);
    graph.add_edge(0, 0, 1, 0);
    graph.compile(48000.0, 16);
    graph.process();

    if (!expect_true(graph.get_node_output_size(1, 0) == 8,
                     "Decimator must divide block size by factor.")) {
        return false;
    }
    if (!expect_true(nearly_equal(graph.get_node_output_sample_rate(1, 0), 24000.0),
                     "Decimator must divide sample rate by factor.")) {
        return false;
    }

    const double* output = graph.get_node_output_buffer(1, 0);
    if (!expect_true(output != nullptr, "Decimator output must be readable.")) return false;

    for (int i = 0; i < 8; ++i) {
        const double expected = static_cast<double>(i * 2);
        if (!nearly_equal(output[i], expected)) {
            std::cout << "FAIL: Decimator sample " << i << " expected " << expected
                      << ", got " << output[i] << ".\n";
            return false;
        }
    }

    return true;
}

bool test_decimator_factor_four() {
    Graph<double> graph;
    auto* source = new SequenceSource();
    auto* decimator = new Decimator<double>();

    graph.add_node(source);
    graph.add_node(decimator);
    graph.set_node_parameter(1, "factor", 4.0);
    graph.add_edge(0, 0, 1, 0);
    graph.compile(48000.0, 16);
    graph.process();

    if (!expect_true(graph.get_node_output_size(1, 0) == 4,
                     "Decimator factor 4 must divide block size by 4.")) {
        return false;
    }
    if (!expect_true(nearly_equal(graph.get_node_output_sample_rate(1, 0), 12000.0),
                     "Decimator factor 4 must divide sample rate by 4.")) {
        return false;
    }

    const double* output = graph.get_node_output_buffer(1, 0);
    if (!expect_true(output != nullptr, "Decimator factor 4 output must be readable.")) {
        return false;
    }

    for (int i = 0; i < 4; ++i) {
        const double expected = static_cast<double>(i * 4);
        if (!nearly_equal(output[i], expected)) {
            std::cout << "FAIL: Decimator factor 4 sample " << i << " expected "
                      << expected << ", got " << output[i] << ".\n";
            return false;
        }
    }

    return true;
}

bool test_windowing_node() {
    Graph<double> graph;
    auto* source = new ConstantSource(1.0);
    auto* windowing = new Windowing<double>();

    graph.add_node(source);
    graph.add_node(windowing);
    graph.set_node_parameter(1, "type", 0.0);
    graph.add_edge(0, 0, 1, 0);
    graph.compile(44100.0, 8);
    graph.process();

    if (!expect_true(graph.get_node_output_size(1, 0) == 8,
                     "Windowing must preserve block size.")) {
        return false;
    }

    const double* output = graph.get_node_output_buffer(1, 0);
    if (!expect_true(output != nullptr, "Windowing output must be readable.")) return false;
    if (!expect_true(nearly_equal(output[0], 0.0, kLooseTolerance),
                     "Hann window first sample must be near zero.")) {
        return false;
    }
    if (!expect_true(nearly_equal(output[7], 0.0, kLooseTolerance),
                     "Hann window last sample must be near zero.")) {
        return false;
    }

    return true;
}

bool test_windowing_hann_values() {
    Graph<double> graph;
    auto* source = new ConstantSource(1.0);
    auto* windowing = new Windowing<double>();

    graph.add_node(source);
    graph.add_node(windowing);
    graph.set_node_parameter(1, "type", 0.0);
    graph.add_edge(0, 0, 1, 0);
    graph.compile(44100.0, 8);
    graph.process();

    const double* output = graph.get_node_output_buffer(1, 0);
    if (!expect_true(output != nullptr, "Hann output must be readable.")) return false;

    for (int i = 0; i < 8; ++i) {
        const double expected = 0.5 * (1.0 - std::cos(2.0 * kPi * i / 7.0));
        if (!nearly_equal(output[i], expected, kLooseTolerance)) {
            std::cout << "FAIL: Hann sample " << i << " expected " << expected
                      << ", got " << output[i] << ".\n";
            return false;
        }
    }

    return true;
}

bool test_windowing_hamming_values() {
    Graph<double> graph;
    auto* source = new ConstantSource(1.0);
    auto* windowing = new Windowing<double>();

    graph.add_node(source);
    graph.add_node(windowing);
    graph.set_node_parameter(1, "type", 1.0);
    graph.add_edge(0, 0, 1, 0);
    graph.compile(44100.0, 8);
    graph.process();

    const double* output = graph.get_node_output_buffer(1, 0);
    if (!expect_true(output != nullptr, "Hamming output must be readable.")) return false;

    for (int i = 0; i < 8; ++i) {
        const double expected = 0.54 - 0.46 * std::cos(2.0 * kPi * i / 7.0);
        if (!nearly_equal(output[i], expected, kLooseTolerance)) {
            std::cout << "FAIL: Hamming sample " << i << " expected " << expected
                      << ", got " << output[i] << ".\n";
            return false;
        }
    }

    return true;
}

bool test_convolution_node() {
    Graph<double> graph;
    auto* source = new SequenceSource();
    auto* convolution = new Convolution<double>();

    graph.add_node(source);
    graph.add_node(convolution);
    graph.set_node_parameter_array(1, "kernel", std::vector<double>{1.0});
    graph.add_edge(0, 0, 1, 0);
    graph.compile(44100.0, 8);
    graph.process();

    const double* output = graph.get_node_output_buffer(1, 0);
    if (!expect_true(output != nullptr, "Convolution output must be readable.")) return false;

    for (int i = 0; i < 8; ++i) {
        const double expected = static_cast<double>(i);
        if (!nearly_equal(output[i], expected)) {
            std::cout << "FAIL: Convolution sample " << i << " expected " << expected
                      << ", got " << output[i] << ".\n";
            return false;
        }
    }

    return true;
}

bool test_convolution_moving_average_kernel() {
    Graph<double> graph;
    auto* source = new SequenceSource();
    auto* convolution = new Convolution<double>();

    graph.add_node(source);
    graph.add_node(convolution);
    graph.set_node_parameter_array(1, "kernel", std::vector<double>{0.5, 0.5});
    graph.add_edge(0, 0, 1, 0);
    graph.compile(44100.0, 8);
    graph.process();

    const double* output = graph.get_node_output_buffer(1, 0);
    if (!expect_true(output != nullptr, "Moving average convolution output must be readable.")) {
        return false;
    }

    const double expected[8] = {0.0, 0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5};
    for (int i = 0; i < 8; ++i) {
        if (!nearly_equal(output[i], expected[i])) {
            std::cout << "FAIL: Moving average convolution sample " << i << " expected "
                      << expected[i] << ", got " << output[i] << ".\n";
            return false;
        }
    }

    return true;
}

bool test_butterworth_filter_node() {
    Graph<double> graph;
    auto* source = new ConstantSource(1.0);
    auto* filter = new ButterworthFilter<double>();

    graph.add_node(source);
    graph.add_node(filter);
    graph.set_node_parameter(1, "cutoff", 1000.0);
    graph.set_node_parameter(1, "type", 0.0);
    graph.add_edge(0, 0, 1, 0);
    graph.compile(44100.0, 16);
    graph.process();

    if (!expect_true(graph.get_node_output_size(1, 0) == 16,
                     "ButterworthFilter must preserve block size.")) {
        return false;
    }

    const double* output = graph.get_node_output_buffer(1, 0);
    if (!expect_true(output != nullptr, "ButterworthFilter output must be readable.")) return false;

    for (int i = 0; i < 16; ++i) {
        if (!std::isfinite(output[i])) {
            std::cout << "FAIL: ButterworthFilter sample " << i << " is not finite.\n";
            return false;
        }
    }

    return true;
}

bool test_butterworth_lowpass_dc_response() {
    Graph<double> graph;
    auto* source = new ConstantSource(1.0);
    auto* filter = new ButterworthFilter<double>();

    graph.add_node(source);
    graph.add_node(filter);
    graph.set_node_parameter(1, "cutoff", 1000.0);
    graph.set_node_parameter(1, "type", 0.0);
    graph.add_edge(0, 0, 1, 0);
    graph.compile(44100.0, 64);
    graph.process();

    const double* output = graph.get_node_output_buffer(1, 0);
    if (!expect_true(output != nullptr, "Butterworth low-pass output must be readable.")) {
        return false;
    }

    for (int i = 0; i < 64; ++i) {
        if (!std::isfinite(output[i])) {
            std::cout << "FAIL: Butterworth low-pass sample " << i << " is not finite.\n";
            return false;
        }
    }

    if (!expect_true(output[63] > output[0],
                     "Butterworth low-pass DC response must rise after startup.")) {
        return false;
    }
    if (!expect_true(output[63] > 0.5 && output[63] < 1.5,
                     "Butterworth low-pass DC response must approach the input level.")) {
        return false;
    }

    return true;
}

bool test_butterworth_highpass_dc_decay() {
    Graph<double> graph;
    auto* source = new ConstantSource(1.0);
    auto* filter = new ButterworthFilter<double>();

    graph.add_node(source);
    graph.add_node(filter);
    graph.set_node_parameter(1, "cutoff", 1000.0);
    graph.set_node_parameter(1, "type", 1.0);
    graph.add_edge(0, 0, 1, 0);
    graph.compile(44100.0, 64);

    for (int block = 0; block < 12; ++block) {
        graph.process();
    }

    const double* output = graph.get_node_output_buffer(1, 0);
    if (!expect_true(output != nullptr, "Butterworth high-pass output must be readable.")) {
        return false;
    }

    for (int i = 0; i < 64; ++i) {
        if (!std::isfinite(output[i])) {
            std::cout << "FAIL: Butterworth high-pass sample " << i << " is not finite.\n";
            return false;
        }
    }

    if (!expect_true(std::abs(output[63]) < 0.05,
                     "Butterworth high-pass DC response must decay toward zero.")) {
        return false;
    }

    return true;
}

bool test_quadrature_modulator_node() {
    Graph<double> graph;
    auto* source = new ConstantSource(2.0);
    auto* modulator = new QuadratureModulator<double>();

    graph.add_node(source);
    graph.add_node(modulator);
    graph.set_node_parameter(1, "frequency", 0.0);
    graph.add_edge(0, 0, 1, 0);
    graph.compile(44100.0, 8);
    graph.process();

    if (!expect_true(graph.get_node_output_size(1, 0) == 8,
                     "QuadratureModulator I output must preserve block size.")) {
        return false;
    }
    if (!expect_true(graph.get_node_output_size(1, 1) == 8,
                     "QuadratureModulator Q output must preserve block size.")) {
        return false;
    }

    const double* out_i = graph.get_node_output_buffer(1, 0);
    const double* out_q = graph.get_node_output_buffer(1, 1);
    if (!expect_true(out_i != nullptr && out_q != nullptr,
                     "QuadratureModulator outputs must be readable.")) {
        return false;
    }

    for (int i = 0; i < 8; ++i) {
        if (!nearly_equal(out_i[i], 2.0, kLooseTolerance)) {
            std::cout << "FAIL: Quadrature I sample " << i << " expected 2, got "
                      << out_i[i] << ".\n";
            return false;
        }
        if (!nearly_equal(out_q[i], 0.0, kLooseTolerance)) {
            std::cout << "FAIL: Quadrature Q sample " << i << " expected 0, got "
                      << out_q[i] << ".\n";
            return false;
        }
    }

    return true;
}

bool test_quadrature_modulator_nonzero_frequency() {
    Graph<double> graph;
    auto* source = new ConstantSource(2.0);
    auto* modulator = new QuadratureModulator<double>();

    graph.add_node(source);
    graph.add_node(modulator);
    graph.set_node_parameter(1, "frequency", 1000.0);
    graph.add_edge(0, 0, 1, 0);
    graph.compile(48000.0, 16);
    graph.process();

    if (!expect_true(graph.get_node_output_size(1, 0) == 16 &&
                     graph.get_node_output_size(1, 1) == 16,
                     "QuadratureModulator nonzero outputs must preserve block size.")) {
        return false;
    }
    if (!expect_true(nearly_equal(graph.get_node_output_sample_rate(1, 0), 48000.0) &&
                     nearly_equal(graph.get_node_output_sample_rate(1, 1), 48000.0),
                     "QuadratureModulator nonzero outputs must preserve sample rate.")) {
        return false;
    }

    const double* out_i = graph.get_node_output_buffer(1, 0);
    const double* out_q = graph.get_node_output_buffer(1, 1);
    if (!expect_true(out_i != nullptr && out_q != nullptr,
                     "QuadratureModulator nonzero outputs must be readable.")) {
        return false;
    }

    for (int i = 0; i < 16; ++i) {
        if (!std::isfinite(out_i[i]) || !std::isfinite(out_q[i])) {
            std::cout << "FAIL: Quadrature nonzero sample " << i << " is not finite.\n";
            return false;
        }
        if (std::abs(out_i[i]) > 2.0 + kLooseTolerance ||
            std::abs(out_q[i]) > 2.0 + kLooseTolerance) {
            std::cout << "FAIL: Quadrature nonzero sample " << i << " exceeds input amplitude.\n";
            return false;
        }
    }

    return true;
}

}  // namespace

int main() {
    std::cout << "--- D(SP)^2 : nodes_cpp smoke test suite ---\n";

    if (!test_constant_node()) return 1;
    if (!test_gain_node()) return 1;
    if (!test_add_node()) return 1;
    if (!test_multiply_node()) return 1;
    if (!test_sine_oscillator_node()) return 1;
    if (!test_sine_oscillator_continuity()) return 1;
    if (!test_noise_generator_node()) return 1;
    if (!test_noise_generator_same_seed_determinism()) return 1;
    if (!test_noise_generator_different_seeds_diverge()) return 1;
    if (!test_audio_file_input_node_streams_samples_and_pads_eof()) return 1;
    if (!test_real_fft_plan_impulse_response()) return 1;
    if (!test_spectrum_analyser_dimensions_and_frequencies()) return 1;
    if (!test_spectrum_analyser_detects_aligned_sine_bin()) return 1;
    if (!test_spectral_peak_picker_selects_strongest_local_peaks()) return 1;
    if (!test_spectral_peak_picker_filters_and_pads()) return 1;
    if (!test_spectral_peak_picker_min_bin_distance_replaces_weaker_neighbor()) return 1;
    if (!test_decimator_node()) return 1;
    if (!test_decimator_factor_four()) return 1;
    if (!test_windowing_node()) return 1;
    if (!test_windowing_hann_values()) return 1;
    if (!test_windowing_hamming_values()) return 1;
    if (!test_convolution_node()) return 1;
    if (!test_convolution_moving_average_kernel()) return 1;
    if (!test_butterworth_filter_node()) return 1;
    if (!test_butterworth_lowpass_dc_response()) return 1;
    if (!test_butterworth_highpass_dc_decay()) return 1;
    if (!test_quadrature_modulator_node()) return 1;
    if (!test_quadrature_modulator_nonzero_frequency()) return 1;

    std::cout << "SUCCESS: nodes_cpp scenarios passed.\n";
    return 0;
}
