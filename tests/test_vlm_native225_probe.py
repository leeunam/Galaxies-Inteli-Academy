"""Small sequential invented Python children; never visual/model processes."""

import json
import os
import subprocess
import sys

import pytest

from scripts import vlm_native225_probe as p


def child(tokens=240, tail="", answer="no"):
    logs = (
        "encoding mtmd batch, n_chunks = 1 (done = 0, total = 1)\n"
        "mtmd batch encoding done in 1 ms\n"
        f"decoding image batch 1/1, n_tokens_batch = {tokens}\n"
        "image decoded (batch 1/1) in 1 ms\n"
    )
    code = f"import sys,os,signal,time;sys.stderr.write({logs!r});sys.stderr.flush();"
    code += f"sys.stdout.write({json.dumps({'answer': answer})!r});sys.stdout.flush();"
    return [sys.executable, "-B", "-c", code + tail]


class Owner:
    def __init__(self):
        self.children = []

    def __call__(self, argv, **kw):
        assert argv[:3] == [sys.executable, "-B", "-c"]
        process = subprocess.Popen(argv, **kw)
        self.children.append(process)
        return process


def run(tmp_path, **kw):
    owner = Owner()
    result = p._run_invented(
        tmp_path, child(**kw), verify=lambda: True, available_bytes=p.MIN_AVAILABLE, launcher=owner
    )
    assert len(owner.children) == 1 and owner.children[0].poll() is not None
    with pytest.raises(ProcessLookupError):
        os.killpg(owner.children[0].pid, 0)
    return result


def test_authority_and_review_and_release_are_required():
    plan = {"plan_sha256": "invented", "execution_released": False}
    with pytest.raises(ValueError, match="authorization_required"):
        p.execute(plan)
    auth = {
        "plan_sha256": "invented",
        "decision": "authorize_native225_once",
        "source_message_id": "invented-human",
    }
    with pytest.raises(ValueError, match="review_required"):
        p.execute(plan, auth)
    review = {
        "plan_sha256": "invented",
        "authorization_sha256": p.base.digest(auth),
        "decision": "reviewed_native225_once",
        "review_message_id": "invented-review",
    }
    with pytest.raises(ValueError, match="not_released"):
        p.execute(plan, auth, review)


def test_exactly_two_argv_values_change():
    original = [
        "runtime",
        "--image-min-tokens",
        "1024",
        "--image-max-tokens",
        "1024",
        "--threads",
        "4",
        "--prompt",
        "unchanged",
    ]
    changed = p.command(original)
    assert sum(a != b for a, b in zip(original, changed, strict=True)) == 2
    assert changed[2] == changed[4] == "225" and original[2] == "1024"


def test_memory_and_authority_refuse_before_spawn(tmp_path):
    for verify, memory in [(lambda: False, p.MIN_AVAILABLE), (lambda: True, 0)]:
        with pytest.raises(ValueError):
            p._run_invented(
                tmp_path,
                [],
                verify=verify,
                available_bytes=memory,
                launcher=lambda *_a, **_k: pytest.fail("spawn"),
            )
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "tokens,answer,technical,correct",
    [
        (240, "no", True, True),
        (239, "no", False, False),
        (241, "no", False, False),
        (240, "yes", True, False),
        (240, "uncertain", True, False),
    ],
)
def test_strict_tokens_and_semantics_and_single_slot(tmp_path, tokens, answer, technical, correct):
    result = run(tmp_path, tokens=tokens, answer=answer)
    assert result["technical_success"] is technical
    assert result["negative_correct"] is correct
    folder = tmp_path / "data/private" / p.durable.NAMESPACE
    assert not (folder / "scratch").exists()
    state = json.loads((folder / "checkpoint.json").read_text())
    assert state["calls"] == 1 and state["sealed"] and state["remaining_calls"] == 0
    with pytest.raises(FileExistsError):
        run(tmp_path)


@pytest.mark.parametrize("cancel", [False, True])
def test_timeout_or_cancel_seals_without_reuse(tmp_path, cancel):
    owner = Owner()
    tail = "os.kill(os.getppid(),signal.SIGTERM);time.sleep(5)" if cancel else "time.sleep(5)"
    result = p._run_invented(
        tmp_path,
        child(tail=tail),
        verify=lambda: True,
        available_bytes=p.MIN_AVAILABLE,
        launcher=owner,
        seconds=0.15,
    )
    assert not result["technical_success"] and owner.children[0].poll() is not None
    folder = tmp_path / "data/private" / p.durable.NAMESPACE
    assert json.loads((folder / "checkpoint.json").read_text())["sealed"]
    with pytest.raises(FileExistsError):
        run(tmp_path)


def test_terminal_capture_is_durable_before_scratch_cleanup(tmp_path, monkeypatch):
    original = p.shutil.rmtree
    checked = []

    def remove(path):
        state = p.durable.inspect(tmp_path, "negative-N")
        assert state["terminal"] and state["cleanup_confirmed"]
        assert state["observation"]["image_tokens_observed"] == 240
        checked.append(True)
        return original(path)

    monkeypatch.setattr(p.shutil, "rmtree", remove)
    assert run(tmp_path)["technical_success"]
    assert checked == [True]
