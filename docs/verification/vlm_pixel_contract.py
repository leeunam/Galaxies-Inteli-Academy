"""Manual synthetic-pixel proof; no model, GGML, decoder, private pixels or network.

Only the three exact source byte streams and the previously pinned compiler are
accepted. This is deliberately outside the default pytest suite.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

from PIL import Image, ImageChops
from PIL import __version__ as pillow_version

SOURCE_HASHES = {
    "mtmd-image.cpp": "2552b9200162160ccb29122371601586c8cd29e5c07f075f0c156f1c47ac38e6",
    "clip-impl.h": "bdaabef3cfce02215d27c7929af398fa3d062041d83216f75a0441d9bd9931e0",
    "clip-model.h": "32c0b4e18e6ad76be843c524a012c1ee0bd07ff78286b2f9bdeee7a8d119f51f",
}
COMPILER_SHA256 = "e6718f7e0c7d057c3ff77b550c603da9bc4030e3ede3c053705acce1293dbe4d"
FLAGS = ["-std=c++17", "-O0", "-Wall", "-Wextra", "-pedantic"]
# Fixed tests and independent expected geometry, defined before execution.
CASES = (
    ("identity", (7, 5), (7, 5), "grid", "PAD_CEIL", (7, 5), (0, 0)),
    ("constant_single", (1, 1), (7, 11), "constant", "PAD_NONE", (7, 11), (0, 0)),
    ("constant_portrait", (360, 640), (800, 1376), "constant", "PAD_CEIL", (775, 1376), (12, 0)),
    ("constant_odd_padding", (5, 5), (9, 12), "constant", "PAD_CEIL", (9, 9), (0, 1)),
    ("rgb_axes", (9, 7), (13, 11), "axes", "PAD_NONE", (13, 11), (0, 0)),
    ("red_impulse", (17, 13), (34, 26), "impulse", "PAD_NONE", (34, 26), (0, 0)),
    ("red_checker", (64, 48), (16, 12), "checker", "PAD_NONE", (16, 12), (0, 0)),
)
SUPPORT = r"""
#include <algorithm>
#include <array>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#define GGML_ASSERT(condition) assert(condition)
// Minimal value type only; no pixel/resampling/normalization function is stubbed.
struct clip_image_size {
    int width, height;
    bool operator==(const clip_image_size & other) const {
        return width == other.width && height == other.height;
    }
};
"""
DRIVER = r"""
struct test_case {
    const char * name;
    int w, h, ow, oh;
    const char * pattern;
    pad_style padding;
};
static std::array<uint8_t, 3> pixel(const std::string & pattern, int x, int y) {
    if (pattern == "constant") return {17, 83, 201};
    if (pattern == "axes") return {uint8_t(x * 20), uint8_t(y * 30), 0};
    if (pattern == "impulse") return {uint8_t(x == 8 && y == 6 ? 255 : 0), 37, 0};
    if (pattern == "checker") return {uint8_t((x + y) % 2 ? 255 : 0), 0, 0};
    return {uint8_t((x * 31 + y * 7) % 256), uint8_t((y * 43 + x * 3) % 256), uint8_t((x * 17 + y * 11) % 256)};
}
int main() {
    const test_case cases[] = {TEST_CASES};
    for (const auto & c : cases) {
        clip_image_u8 src, dst;
        src.set_size({c.w, c.h}, false);
        for (int y = 0; y < c.h; ++y)
            for (int x = 0; x < c.w; ++x) src.set_pixel(x, y, pixel(c.pattern, x, y));
        img_tool::resize(src, dst, {c.ow, c.oh}, RESIZE_ALGO_BICUBIC, c.padding);
        const auto & raw = dst.get_ro_buf();
        std::cout << c.name << " " << dst.get_size().width << " " << dst.get_size().height << " " << raw.size() << "\n";
        std::cout.write(reinterpret_cast<const char *>(raw.data()), raw.size());
        std::cout << "\n";
    }
}
"""


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def block(raw, marker):
    start = raw.index(marker)
    end = raw.index(b"\n};", start) + 3
    return raw[start:end]  # exact bytes; no rewriting inside the extracted block


def generated_input(size, pattern):
    image = Image.new("RGB", size)
    for y in range(size[1]):
        for x in range(size[0]):
            if pattern == "constant":
                rgb = (17, 83, 201)
            elif pattern == "axes":
                rgb = (x * 20, y * 30, 0)
            elif pattern == "impulse":
                rgb = (255 if (x, y) == (8, 6) else 0, 37, 0)
            elif pattern == "checker":
                rgb = (255 if (x + y) % 2 else 0, 0, 0)
            else:
                rgb = ((x * 31 + y * 7) % 256, (y * 43 + x * 3) % 256, (x * 17 + y * 11) % 256)
            image.putpixel((x, y), rgb)
    return image


def run_test(command, folder, *, name, timeout):
    """Own only the compiler or this fixed stdlib test, never a model process."""
    started = time.monotonic()
    child = subprocess.Popen(
        command,
        cwd=folder,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        out, err = child.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGKILL)
        out, err = child.communicate(timeout=5)
        (folder / (name + ".stdout")).write_bytes(out)
        (folder / (name + ".stderr")).write_bytes(err)
        raise RuntimeError(name + "_timeout") from None
    finally:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait(timeout=5)
    (folder / (name + ".stdout")).write_bytes(out)
    (folder / (name + ".stderr")).write_bytes(err)
    if child.returncode != 0:
        raise RuntimeError(name + "_failed")
    return out, {
        "exitcode": child.returncode,
        "seconds": time.monotonic() - started,
        "stdout_bytes": len(out),
        "stderr_bytes": len(err),
        "stderr_sha256": sha(err),
    }


def check_case(case, raw):
    name, source_size, target, pattern, _, content, offset = case
    output = Image.frombytes("RGB", target, raw)
    source = generated_input(source_size, pattern)
    checks = {"rgb_byte_count": len(raw) == target[0] * target[1] * 3}
    if name == "identity":
        checks["identity_rgb_order_and_row_stride"] = raw == source.tobytes()
    if pattern == "constant":
        expected = Image.new("RGB", target)
        expected.paste(Image.new("RGB", content, (17, 83, 201)), offset)
        checks["constant_rgb_and_exact_padding"] = raw == expected.tobytes()
    if pattern == "axes":
        channels = output.split()
        checks["blue_stays_zero"] = channels[2].getextrema() == (0, 0)
        checks["red_independent_of_y"] = all(
            output.getpixel((x, y))[0] == output.getpixel((x, 0))[0]
            for y in range(target[1])
            for x in range(target[0])
        )
        checks["green_independent_of_x"] = all(
            output.getpixel((x, y))[1] == output.getpixel((0, y))[1]
            for y in range(target[1])
            for x in range(target[0])
        )
        checks["axes_keep_orientation"] = all(
            output.getpixel((x, 0))[0] <= output.getpixel((x + 1, 0))[0]
            for x in range(target[0] - 1)
        ) and all(
            output.getpixel((0, y))[1] <= output.getpixel((0, y + 1))[1]
            for y in range(target[1] - 1)
        )
    if pattern == "impulse":
        red, green, blue = output.split()
        bbox = red.getbbox()
        checks["red_nonzero_local_support"] = (
            bbox is not None and 13 <= bbox[0] < bbox[2] <= 21 and 9 <= bbox[1] < bbox[3] <= 17
        )
        checks["green_constant_blue_zero"] = green.getextrema() == (
            37,
            37,
        ) and blue.getextrema() == (0, 0)
    if pattern == "checker":
        red, green, blue = output.split()
        checks["downsample_has_intermediate_values"] = any(0 < n < 255 for n in red.tobytes())
        checks["no_channel_leakage"] = green.getextrema() == blue.getextrema() == (0, 0)
    # Exploratory comparison only. A difference is never itself a failed invariant.
    reference = Image.new("RGB", target)
    reference.paste(source.resize(content, Image.Resampling.BICUBIC), offset)
    difference = ImageChops.difference(output, reference)
    reference_raw = reference.tobytes()
    return {
        "case": name,
        "source": list(source_size),
        "canvas": list(target),
        "content": list(content),
        "offset": list(offset),
        "input_sha256": sha(source.tobytes()),
        "output_sha256": sha(raw),
        "checks": checks,
        "invariants_passed": all(checks.values()),
        "pillow_exploratory": {
            "authority_for_model": False,
            "equal_bytes": raw == reference_raw,
            "different_channel_bytes": sum(a != b for a, b in zip(raw, reference_raw, strict=True)),
            "maximum_absolute_channel_difference": max(v[1] for v in difference.getextrema()),
        },
    }


def synthetic_loss_check():
    """Two invented RGB images through the declared legacy recipe, in memory."""
    original = Image.new("RGB", (360, 640), (128, 128, 128))
    changed = original.copy()
    changed.putpixel((180, 320), (129, 128, 128))
    stages = []
    for image in (original, changed):
        before = sha(image.tobytes())
        thumb = image.copy()
        thumb.thumbnail((512, 512))
        thumbnail_hash = sha(thumb.tobytes())
        encoded = io.BytesIO()
        thumb.save(encoded, format="JPEG")  # Same Pillow default as the frozen recipe.
        with Image.open(io.BytesIO(encoded.getvalue())) as jpeg:
            jpeg.load()
            jpeg.thumbnail((320, 330))
            content_size = list(jpeg.size)
            restored = jpeg.resize((360, 640), Image.Resampling.LANCZOS)
        stages.append(
            {
                "native_rgb_sha256": before,
                "thumbnail_rgb_sha256": thumbnail_hash,
                "jpeg_sha256": sha(encoded.getvalue()),
                "content_size": content_size,
                "restored_rgb_sha256": sha(restored.tobytes()),
            }
        )
    return {
        "entirely_generated": True,
        "pipeline_replica_not_real_frames": True,
        "jpeg_isolation_claim": False,
        "perceptual_quality_claim": False,
        "native_inputs_differ": stages[0]["native_rgb_sha256"] != stages[1]["native_rgb_sha256"],
        "restored_outputs_equal": stages[0]["restored_rgb_sha256"]
        == stages[1]["restored_rgb_sha256"],
        "stages": stages,
    }


def new_work_path(work):
    # absolute() preserves symlinks, so a dangling destination stays rejected.
    work = work.absolute()
    if work.exists() or work.is_symlink():
        raise ValueError("new_empty_work_directory_required")
    return work


def audit(source_folder, work):
    work = new_work_path(work)
    sources = {}
    for name, wanted in SOURCE_HASHES.items():
        path = source_folder / name
        if path.is_symlink() or path.stat().st_size > 100000:
            raise ValueError("source_identity_rejected")
        raw = path.read_bytes()
        if sha(raw) != wanted:
            raise ValueError("source_identity_rejected")
        sources[name] = raw
    compiler = Path(shutil.which("g++") or "missing-compiler").resolve()
    if not compiler.is_file() or sha(compiler.read_bytes()) != COMPILER_SHA256:
        raise ValueError("compiler_identity_rejected")
    extracted = {
        "resize_algo": block(sources["clip-model.h"], b"enum resize_algo {"),
        "pad_style": block(sources["clip-model.h"], b"enum pad_style {"),
        "clip_image_u8": block(sources["clip-impl.h"], b"struct clip_image_u8 {"),
        "img_tool": block(sources["mtmd-image.cpp"], b"struct img_tool {"),
    }
    cases = ",\n".join(
        f'{{"{name}",{size[0]},{size[1]},{target[0]},{target[1]},"{pattern}",{padding}}}'
        for name, size, target, pattern, padding, _, _ in CASES
    )
    source = (
        SUPPORT.encode()
        + b"\n".join(extracted.values())
        + DRIVER.replace("TEST_CASES", cases).encode()
    )
    work.mkdir(mode=0o700)
    (work / "proof.cpp").write_bytes(source)
    report = {
        "protocol": "fixed-source-synthetic-pixel-proof-v1",
        "source_commit": "797de63b2",
        "sources_sha256": SOURCE_HASHES,
        "extracted_blocks_sha256": {k: sha(v) for k, v in extracted.items()},
        "harness_sha256": sha(Path(__file__).read_bytes()),
        "generated_cpp_sha256": sha(source),
        "compiler_sha256": COMPILER_SHA256,
        "compiler_flags": FLAGS,
        "pillow_version": pillow_version,
        "model_loaded": False,
        "forward_passes": 0,
        "real_images_opened": 0,
        "png_loader_exercised": False,
        "model_dispatch_exercised": False,
        "patch_merger_exercised": False,
        "normalization_exercised": False,
        "one_compile_one_execution": True,
    }
    try:
        _, report["compile"] = run_test(
            [str(compiler), *FLAGS, "proof.cpp", "-o", "proof"], work, name="compile", timeout=20
        )
        report["test_binary_sha256"] = sha((work / "proof").read_bytes())
        raw, report["execution"] = run_test(
            [str(work / "proof")], work, name="execution", timeout=10
        )
        stream = io.BytesIO(raw)
        results = []
        for case in CASES:
            name, width, height, count = stream.readline(200).decode("ascii").split()
            width, height, count = int(width), int(height), int(count)
            if name != case[0] or (width, height) != case[2] or count != width * height * 3:
                raise ValueError("fixed_output_shape_failed")
            pixels = stream.read(count)
            if len(pixels) != count or stream.read(1) != b"\n":
                raise ValueError("fixed_output_length_failed")
            results.append(check_case(case, pixels))
        if stream.read(1):
            raise ValueError("unexpected_output_tail")
        report["synthetic_information_loss"] = synthetic_loss_check()
        report.update(cases=results, invariants_passed=all(v["invariants_passed"] for v in results))
    except Exception as exc:
        report.update(invariants_passed=False, failure_type=type(exc).__name__)
        raise
    finally:
        (work / "receipt.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    try:
        value = audit(args.sources, args.work)
        print(
            json.dumps(
                {
                    "cases": len(value["cases"]),
                    "invariants_passed": value["invariants_passed"],
                    "model_loaded": False,
                    "forward_passes": 0,
                }
            )
        )
        raise SystemExit(0 if value["invariants_passed"] else 1)
    except Exception as exc:  # noqa: BLE001 -- never print a private source/work locator
        print(json.dumps({"status": "proof_stopped", "error_type": type(exc).__name__}))
        raise SystemExit(1) from None
