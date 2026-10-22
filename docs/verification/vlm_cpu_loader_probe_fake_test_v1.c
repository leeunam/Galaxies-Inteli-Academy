/* Link-free fake GGML API. This test must never link a GGML DSO. */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#define main probe_main
#include "vlm_cpu_loader_probe_v1.c"
#undef main

static ggml_log_callback fake_logger;
static void * fake_data;
static int scenario, calls, log_sets, counts, gets, names;
static int reg_token;

void ggml_log_set(ggml_log_callback callback, void * data) {
    ++log_sets;
    fake_logger = callback;
    fake_data = data;
}

void ggml_backend_load_all_from_path(const char * path) {
    static const char line[] = "load_backend: loaded CPU backend from /bundle/libggml-cpu-alderlake.so\n";
    ++calls;
    assert(!strcmp(path, "/bundle"));
    puts("NEVER_PROJECT direct library stdout");
    fflush(stdout);
    if (scenario == 1) {
        fake_logger(GGML_LOG_LEVEL_INFO,
                    "load_backend: loaded CPU backend from /bundle/libggml-cpu-x64.so\n", fake_data);
    } else if (scenario == 2) {
        fake_logger(GGML_LOG_LEVEL_INFO,
                    "load_backend: loaded CPU backend from /bundle/NEVER_PROJECT.so\n", fake_data);
    } else if (scenario == 3) {
        fake_logger(GGML_LOG_LEVEL_INFO,
                    "load_backend: loaded RPC backend from /bundle/libggml-rpc.so\n", fake_data);
    } else if (scenario == 10) {
        char huge[1024];
        memset(huge, 'X', sizeof(huge));
        memcpy(huge, "load_backend: loaded ", 21);
        huge[sizeof(huge) - 1] = 0;
        fake_logger(GGML_LOG_LEVEL_INFO, huge, fake_data);
    } else {
        if (scenario == 4) fake_logger(GGML_LOG_LEVEL_ERROR, "NEVER_PROJECT unknown log\n", fake_data);
        if (scenario == 9) fake_logger(GGML_LOG_LEVEL_INFO, NULL, fake_data);
        fake_logger(scenario == 6 ? GGML_LOG_LEVEL_WARN : GGML_LOG_LEVEL_INFO, line, fake_data);
        if (scenario == 5) fake_logger(GGML_LOG_LEVEL_INFO, line, fake_data);
    }
}

size_t ggml_backend_reg_count(void) { ++counts; return scenario == 7 ? 2 : 1; }
ggml_backend_reg_t ggml_backend_reg_get(size_t index) {
    ++gets;
    assert(index == 0);
    return (ggml_backend_reg_t)&reg_token;
}
const char * ggml_backend_reg_name(ggml_backend_reg_t reg) {
    ++names;
    assert(reg == (ggml_backend_reg_t)&reg_token);
    return scenario == 8 ? "NEVER_PROJECT" : "CPU";
}

int main(void) {
    int saved_stdout = dup(STDOUT_FILENO);
    assert(saved_stdout >= 0);
    for (scenario = 0; scenario <= 10; ++scenario) {
        assert(dup2(saved_stdout, STDOUT_FILENO) >= 0);
        calls = log_sets = counts = gets = names = 0;
        int result = probe_main(1, NULL);
        int accepted = scenario == 0 || scenario == 1 || scenario == 4 || scenario == 9;
        assert(result == (accepted ? 0 : 65));
        assert(calls == 1 && log_sets == 1);
        assert(counts <= 1 && gets <= 1 && names <= 1);
        if (accepted) assert(counts == 1 && gets == 1 && names == 1);
    }
    calls = log_sets = 0;
    assert(probe_main(2, NULL) == 64);
    assert(calls == 0 && log_sets == 0);
    assert(dup2(saved_stdout, STDOUT_FILENO) >= 0);
    close(saved_stdout);
    return 0;
}
