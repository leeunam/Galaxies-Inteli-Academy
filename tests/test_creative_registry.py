import json
import os
import subprocess

import pytest

from scripts.creative_analysis import analyze_creatives
from scripts.creative_contracts import ErrorResponse
from scripts.creative_media import MAX_BYTES, CreativeError, inspect_media
from scripts.creative_registry import CreativeRegistry


def register(registry, path):
    return registry.register({"campaign_id": "demo", "sector": "moda", "relative_path": path})


def analyze(registry, creative_id):
    return analyze_creatives(
        {
            "campaign_id": "demo",
            "creative_ids": [creative_id],
            "sector": "moda",
            "objective": "divulgacao",
            "brief": "Coleção.",
        },
        registry,
    )


def test_registration_persists_private_mapping_but_exposes_only_opaque_id(registry, registered):
    assert set(registered) == {"schema_version", "status", "creative_id", "campaign_id", "sector"}
    assert len(registered["creative_id"]) == 35
    assert os.stat(registry.registry_file).st_mode & 0o777 == 0o600
    restarted = CreativeRegistry(registry.uploads_root, registry.registry_file)
    assert analyze(restarted, registered["creative_id"])["status"] == "prediction_unavailable"


@pytest.mark.parametrize("path", ["../outside.mp4", "/tmp/outside.mp4", "https://secret/video.mp4"])
def test_paths_outside_root_and_urls_are_rejected(registry, path):
    result = register(registry, path)
    ErrorResponse.model_validate(result)
    assert result["error"]["code"] == "unsafe_path"
    assert path not in json.dumps(result)


@pytest.mark.parametrize("directory", [False, True])
def test_symlink_escape_is_rejected_at_each_component(registry, tmp_path, video_factory, directory):
    outside = tmp_path / "outside"
    video_factory(outside / "secret.mp4")
    link = registry.uploads_root / "escape"
    link.symlink_to(outside if directory else outside / "secret.mp4")
    path = "escape/secret.mp4" if directory else "escape"
    assert register(registry, path)["error"]["code"] == "unsafe_path"


def test_file_replaced_by_symlink_after_registration_is_rejected(registry, registered, tmp_path):
    media = registry.uploads_root / "demo.mp4"
    outside = tmp_path / "private.mp4"
    media.rename(outside)
    media.symlink_to(outside)
    assert analyze(registry, registered["creative_id"])["error"]["code"] == "unsafe_path"


def test_changed_media_requires_new_registration(registry, registered, video_factory):
    video_factory(registry.uploads_root / "demo.mp4", frames=3)
    assert analyze(registry, registered["creative_id"])["error"]["code"] == "media_changed"


def test_missing_media_is_explicit(registry, registered):
    (registry.uploads_root / "demo.mp4").unlink()
    assert analyze(registry, registered["creative_id"])["error"]["code"] == "media_missing"


def test_extension_alone_does_not_establish_video_type(registry):
    (registry.uploads_root / "fake.mp4").write_text("DADO_PRIVADO")
    result = register(registry, "fake.mp4")
    assert result["error"]["code"] == "invalid_media"
    assert "DADO_PRIVADO" not in json.dumps(result)
    assert not registry.registry_file.exists()


@pytest.mark.parametrize("options", [{"width": 96, "height": 64}, {"frames": 61, "rate": 1}])
def test_landscape_and_long_video_exceed_scope(registry, video_factory, options):
    video_factory(registry.uploads_root / "invalid.mp4", **options)
    assert register(registry, "invalid.mp4")["error"]["code"] == "media_limits_exceeded"


def test_byte_limit_checked_before_decoding(registry):
    with (registry.uploads_root / "huge.mp4").open("wb") as handle:
        handle.truncate(MAX_BYTES + 1)
    assert register(registry, "huge.mp4")["error"]["code"] == "media_limits_exceeded"


def test_fifo_cannot_block_registration(registry):
    os.mkfifo(registry.uploads_root / "pipe.mp4")
    assert register(registry, "pipe.mp4")["error"]["code"] == "invalid_media"


def test_corrupt_registry_is_safe_failure(registry, registered):
    registry.registry_file.write_text("DADO_PRIVADO_INVALIDO")
    result = analyze(registry, registered["creative_id"])
    assert result["error"]["code"] == "registry_unavailable"
    assert "DADO_PRIVADO" not in json.dumps(result)


def test_inspection_timeout_is_structured_and_does_not_forward_secrets(
    registry, registered, monkeypatch
):
    monkeypatch.setenv("NVIDIA_API_KEY", "DADO_PRIVADO")

    def timeout(*args, **kwargs):
        assert "NVIDIA_API_KEY" not in kwargs["env"]
        raise subprocess.TimeoutExpired(args[0], 30)

    monkeypatch.setattr(subprocess, "run", timeout)
    result = analyze(registry, registered["creative_id"])
    assert result["error"]["code"] == "media_timeout"


def test_decoder_crash_becomes_safe_error(registry, registered, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 1))
    with registry.open_media("demo.mp4") as handle, pytest.raises(CreativeError) as error:
        inspect_media(handle)
    assert error.value.code == "invalid_media"
