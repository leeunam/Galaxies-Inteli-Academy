/* Review candidate only; never run outside the documented CPU-only capsule.
 * ggml.h is supplied by the separately verified official text, not vendored.
 * Opaque registry/prototypes below are copied from ggml-backend.h:29,202,238-239,262.
 * No backend stream, tensor, model, encoder or graph API is called here.
 */
#define _POSIX_C_SOURCE 200809L
#include "ggml.h"
#include <stdio.h>
#include <string.h>
#include <unistd.h>

typedef struct ggml_backend_reg * ggml_backend_reg_t;
extern void ggml_backend_load_all_from_path(const char * dir_path);
extern size_t ggml_backend_reg_count(void);
extern ggml_backend_reg_t ggml_backend_reg_get(size_t index);
extern const char * ggml_backend_reg_name(ggml_backend_reg_t reg);

static const char * const variants[] = {
    "libggml-cpu-alderlake.so", "libggml-cpu-cannonlake.so",
    "libggml-cpu-cascadelake.so", "libggml-cpu-cooperlake.so",
    "libggml-cpu-haswell.so", "libggml-cpu-icelake.so",
    "libggml-cpu-ivybridge.so", "libggml-cpu-piledriver.so",
    "libggml-cpu-sandybridge.so", "libggml-cpu-sapphirerapids.so",
    "libggml-cpu-skylakex.so", "libggml-cpu-sse42.so",
    "libggml-cpu-x64.so", "libggml-cpu-zen4.so"
};

struct observation {
    int selected;
    unsigned loaded_lines; /* Saturates at two: duplicate registration fails. */
    int invalid_loaded_line;
};

static void observe_log(enum ggml_log_level level, const char * text, void * data) {
    static const char prefix[] = "load_backend: loaded ";
    struct observation * state = data;
    size_t n = 0;
    if (!text) return;
    while (n < 256 && text[n]) ++n;
    if (n < sizeof(prefix) - 1 || memcmp(text, prefix, sizeof(prefix) - 1)) return;
    if (state->loaded_lines < 2) ++state->loaded_lines;
    if (n == 256 || level != GGML_LOG_LEVEL_INFO) {
        state->invalid_loaded_line = 1;
        return;
    }
    for (size_t i = 0; i < sizeof(variants) / sizeof(variants[0]); ++i) {
        char expected[128];
        int len = snprintf(expected, sizeof(expected),
                           "load_backend: loaded CPU backend from /bundle/%s\n", variants[i]);
        if (len > 0 && (size_t)len == n && !memcmp(text, expected, n)) {
            state->selected = (int)i;
            return;
        }
    }
    state->invalid_loaded_line = 1;
}

static int rejected(FILE * report) {
    int ok = fputs("{\"observed\":false,\"code\":\"selection_not_confirmed\"}\n", report) >= 0;
    if (fclose(report)) ok = 0;
    return ok ? 65 : 74;
}

int main(int argc, char ** argv) {
    /* Logger data survives main through any library finalizers. */
    static struct observation state;
    (void)argv;
    if (argc != 1) return 64;
    int fd = dup(STDOUT_FILENO);
    if (fd < 0) return 74;
    FILE * report = fdopen(fd, "w");
    if (!report) { close(fd); return 74; }
    /* Capsule stderr is /dev/null. Discard direct library stdout as well. */
    if (dup2(STDERR_FILENO, STDOUT_FILENO) < 0) { fclose(report); return 74; }
    state = (struct observation){ -1, 0, 0 };
    ggml_log_set(observe_log, &state);
    ggml_backend_load_all_from_path("/bundle");
    if (state.selected < 0 || state.loaded_lines != 1 || state.invalid_loaded_line) return rejected(report);
    if (ggml_backend_reg_count() != 1) return rejected(report);
    ggml_backend_reg_t reg = ggml_backend_reg_get(0);
    if (!reg) return rejected(report);
    const char * name = ggml_backend_reg_name(reg);
    if (!name || strncmp(name, "CPU", 4)) return rejected(report);
    int ok = fprintf(report, "{\"observed\":true,\"scope\":\"current_capsule_only\",\"variant\":\"%s\"}\n",
                     variants[state.selected]) > 0;
    if (fclose(report)) ok = 0;
    return ok ? 0 : 74;
}
