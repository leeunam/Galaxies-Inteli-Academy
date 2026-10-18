"""Prepare only pinned official CPU artifacts; no user media or credentials are needed."""

import argparse
import hashlib
import json
import platform
import tarfile
import urllib.request

from scripts.gguf_visual_attributes import HASHES, MODEL_DIR, REVISION, ROOT, RUNTIME

ARCHIVE_SHA256 = "8c08b19bee40d118b803d58fd8f6633ba311ce3c7f1f0138262e636f02aa11f0"
ARCHIVE_URL = "https://github.com/ggml-org/llama.cpp/releases/download/b11716/llama-b11716-bin-ubuntu-x64.tar.gz"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def prepare(offline=False):
    from huggingface_hub import snapshot_download

    if platform.system() != "Linux" or platform.machine() not in {"x86_64", "AMD64"}:
        raise ValueError("Pinned pilot runtime requires Linux x64")
    root = ROOT / "data/cache/llama-cpp/b11716"
    root.mkdir(parents=True, exist_ok=True)
    archive = root / "runtime.tar.gz"
    if not archive.exists():
        if offline:
            raise ValueError("Pinned runtime archive is absent from the local cache")
        request = urllib.request.Request(
            ARCHIVE_URL, headers={"User-Agent": "Galaxies-Quality-Pilot/0.1"}
        )
        partial = root / "runtime.tar.part"
        size = 0
        try:
            with (
                urllib.request.urlopen(request, timeout=30) as response,
                partial.open("wb") as target,
            ):
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > 20 * 1024 * 1024:
                        raise ValueError("CPU runtime archive byte limit exceeded")
                    target.write(chunk)
            if sha256(partial) != ARCHIVE_SHA256:
                raise ValueError("CPU runtime does not match the official SHA256")
            partial.replace(archive)
        finally:
            partial.unlink(missing_ok=True)
    if sha256(archive) != ARCHIVE_SHA256:
        raise ValueError("Cached CPU runtime archive SHA256 mismatch")
    # Reinstall executable and shared libraries from the verified archive. Merely
    # finding an old executable would not verify the runtime used by this batch.
    with tarfile.open(archive) as bundle:
        if sum(m.size for m in bundle.getmembers()) > 128 * 1024 * 1024:
            raise ValueError("Runtime extraction byte limit exceeded")
        bundle.extractall(root, filter="data")
    snapshot_download(
        "Qwen/Qwen3-VL-2B-Instruct-GGUF",
        revision=REVISION,
        allow_patterns=list(HASHES),
        token=False,
        max_workers=2,
        local_files_only=offline,
        cache_dir=str(ROOT / "data/cache/huggingface/hub"),
    )
    for filename, expected in HASHES.items():
        if sha256(MODEL_DIR / filename) != expected:
            raise ValueError("Official GGUF weight SHA256 mismatch: " + filename)
    return {
        "status": "verified",
        "runtime_release": "b11716",
        "model_revision": REVISION,
        "runtime_archive_sha256": ARCHIVE_SHA256,
        "installed_executable_sha256": sha256(RUNTIME),
        "weights_sha256": HASHES,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    print(json.dumps(prepare(args.offline)))
