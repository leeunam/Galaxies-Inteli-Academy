// Model-free bridge to the *installed* b11716 converter and grammar validator.
// Official headers are separately pinned; no runtime implementation is compiled.
#include "json.h"
#include "llama-grammar.h"

#include <algorithm>
#include <fstream>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>

// Exact declaration from b11716/common/json-schema-to-grammar.h.
std::string json_schema_to_grammar(const common_json & schema, bool force_gbnf = false);

static std::string read_file(const char * path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("input_unavailable");
    std::ostringstream output;
    output << input.rdbuf();
    return output.str();
}

using grammar_ptr = std::unique_ptr<llama_grammar, decltype(&llama_grammar_free_impl)>;

int main(int argc, char ** argv) {
    try {
        if (argc != 4) throw std::runtime_error("expected_schema_probes_grammar_paths");
        const auto schema = common_json::parse(read_file(argv[1]));
        // false matches the adapter's --json-schema-file conversion path.
        const auto grammar = json_schema_to_grammar(schema, false);
        grammar_ptr base(llama_grammar_init_impl(nullptr, grammar.c_str(), "root", false,
                                                nullptr, 0, nullptr, 0), llama_grammar_free_impl);
        if (!base) throw std::runtime_error("native_grammar_init_failed");
        std::ofstream grammar_output(argv[3]);
        if (!grammar_output) throw std::runtime_error("grammar_output_unavailable");
        grammar_output << grammar;
        grammar_output.close();
        std::ifstream probes(argv[2]);
        if (!probes) throw std::runtime_error("probes_unavailable");
        std::string line;
        size_t index = 0;
        while (std::getline(probes, line)) {
            const auto probe = common_json::parse(line);
            const auto raw = probe["raw"].get<std::string>();
            grammar_ptr current(llama_grammar_clone_impl(*base), llama_grammar_free_impl);
            if (!current) throw std::runtime_error("native_grammar_clone_failed");
            for (unsigned char byte : raw) {
                if (byte >= 128) throw std::runtime_error("probe_must_be_ascii");
                if (llama_grammar_get_stacks(current.get()).empty()) break;
                llama_grammar_accept(current.get(), byte);
            }
            const auto & stacks = llama_grammar_get_stacks(current.get());
            const bool accepted = std::any_of(stacks.begin(), stacks.end(),
                                              [](const auto & stack) { return stack.empty(); });
            std::cout << "{\"index\":" << index++ << ",\"accepted\":"
                      << (accepted ? "true" : "false") << "}\n";
        }
        return 0;
    } catch (const std::exception &) {
        std::cerr << "native_grammar_preflight_failed\n";
        return 1;
    }
}
