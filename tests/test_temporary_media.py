import json
from pathlib import Path

import pytest

from scripts.pilot_licensed_media import (
    atomic_json,
    frames_and_properties,
    run_session,
    select_vlm_samples,
)
from scripts.visual_attributes import validate_vlm_answer


def fake_download(path: Path) -> dict:
    path.write_bytes(b"fixture")
    path.with_suffix(".part").write_bytes(b"partial")
    return {"sha256": "synthetic-test-fingerprint"}


def test_success_persists_attributes_without_media(tmp_path):
    def extract(media, scratch):
        assert media.read_bytes() == b"fixture"
        (scratch / "frame.jpg").write_bytes(b"frame")
        return {"synthetic_feature": 42}

    output, scratch = tmp_path / "output", tmp_path / "scratch"
    state = run_session(output, scratch, extract, fake_download)
    assert state["status"] == "completed"
    assert state["temporary_directory_removed"]
    assert list(scratch.iterdir()) == []
    assert json.loads((output / "features.json").read_text()) == {"synthetic_feature": 42}
    assert sorted(x.name for x in output.iterdir()) == ["features.json", "run.json"]
    assert not state["training_eligible"]


@pytest.mark.parametrize("fail_during", ["download", "extraction"])
def test_failure_cleans_partial_media_and_records_failure(tmp_path, fail_during):
    def download(media):
        result = fake_download(media)
        if fail_during == "download":
            raise RuntimeError("synthetic download failure")
        return result

    def extract(media, scratch):
        (scratch / "audio.raw").write_bytes(b"audio")
        raise RuntimeError("synthetic extractor failure")

    output, scratch = tmp_path / "output", tmp_path / "scratch"
    with pytest.raises(RuntimeError):
        run_session(output, scratch, extract, download)
    state = json.loads((output / "run.json").read_text())
    assert state["status"] == "failed"
    assert state["temporary_directory_removed"]
    assert list(scratch.iterdir()) == []
    assert not (output / "features.json").exists()


def test_invalid_artifact_does_not_overwrite_previous_result(tmp_path):
    artifact = tmp_path / "features.json"
    atomic_json(artifact, {"previous": True})
    with pytest.raises(ValueError):
        atomic_json(artifact, {"invalid": float("nan")})
    assert json.loads(artifact.read_text()) == {"previous": True}
    assert sorted(x.name for x in tmp_path.iterdir()) == ["features.json"]


def test_parseable_vlm_output_without_evidence_is_rejected():
    answer = {
        "person_visible": True,
        "product_visible_early": True,
        "product_closeup": True,
        "demonstration": True,
        "screen_text": "TV Brasil",
        "scene": "Scene 1",
        "format": "TV Brasil",
    }
    status, _ = validate_vlm_answer(json.dumps(answer))
    assert status == "invalid_schema"


def test_late_frame_cannot_support_a_claim_about_the_first_three_seconds():
    fields = [
        "person_visible",
        "product_visible_early",
        "product_closeup",
        "demonstration",
        "screen_text",
        "scene",
        "format",
    ]
    answer = {key: {"value": "unknown", "frames": []} for key in fields}
    assert validate_vlm_answer(json.dumps(answer))[0] == "schema_valid_requires_perception_review"
    answer["product_visible_early"] = {"value": True, "frames": [4]}
    assert validate_vlm_answer(json.dumps(answer))[0] == "invalid_early_frame_evidence"


def test_vlm_sampling_uses_timestamps_for_short_and_deduplicated_video_samples():
    paths = list(map(Path, ["a", "b", "c", "d", "e", "f"]))
    properties = {
        "duration_seconds": 8,
        "sampled_frame_seconds": [0.2, 1.5, 2.4, 2.8, 4.8, 7.2],
    }
    selected, seconds = select_vlm_samples(paths, properties)
    assert selected == [paths[i] for i in [0, 1, 3, 4]]
    assert seconds == [0.2, 1.5, 2.8, 4.8]
    short_paths, short_seconds = select_vlm_samples(
        paths[:2], {"duration_seconds": 0.2, "sampled_frame_seconds": [0.06, 0.16]}
    )
    assert short_paths == [paths[1]]
    assert short_seconds == [0.16]


@pytest.mark.parametrize("frames", [1, 2, 8, 40])
def test_actual_tiny_video_keeps_real_unique_frames_and_does_not_invent_timestamps(
    tmp_path, video_factory, frames
):
    path = video_factory(tmp_path / "tiny.mp4", frames=frames, rate=10)
    properties, paths = frames_and_properties(path, tmp_path)
    seconds = properties["sampled_frame_seconds"]
    assert seconds == sorted(set(seconds))
    assert 1 <= len(paths) == len(seconds) <= min(6, frames)
    assert all(t * 10 == pytest.approx(round(t * 10)) for t in seconds)
    assert all(0 <= t < properties["duration_seconds"] for t in seconds)
    assert all(p.is_file() for p in paths)
