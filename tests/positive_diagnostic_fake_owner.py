"""Load diagnostic source with an invented owner before executing its imports."""

import _io
import builtins
import importlib.abc
import importlib.machinery
import importlib.util
import io
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

PRIVATE_OWNER = Path(
    "/home/inteli/Documents/projetos/Galaxies-Inteli-Academy/"
    "data/private/issue-4-visual-validation-run-v2/control_operator.py"
)


def no_child(*_args, **_kwargs):
    raise AssertionError("invented_owner_child_execution_forbidden")


class InventedOwnerLoader(importlib.abc.Loader):
    def create_module(self, spec):
        return None

    def exec_module(self, module):
        module.fixture_origin = "invented_no_private_source"
        module.supervisor = SimpleNamespace(proc_identity=no_child)
        module.owned_run = no_child
        module.capsule = no_child


@contextmanager
def invented_operator(script, tmp_path, monkeypatch):
    private_reads, intercepted = [], []

    def reject_private(path):
        try:
            name = Path(os.fsdecode(os.fspath(path))).absolute()
        except TypeError:  # Public file descriptors are not private source paths.
            return
        if name == PRIVATE_OWNER:
            private_reads.append(str(name))
            raise AssertionError("private_owner_read_forbidden")

    for obj, attribute in (
        (builtins, "open"),
        (io, "open"),
        (_io, "open_code"),
        (os, "open"),
    ):
        original = getattr(obj, attribute)

        def guarded(path, *args, _original=original, **kwargs):
            reject_private(path)
            return _original(path, *args, **kwargs)

        monkeypatch.setattr(obj, attribute, guarded)

    # These imports are public. No private owner is loaded by either helper.
    from scripts import visual_validation_batch_v1 as batch
    from scripts import visual_validation_capture_v1 as capture

    before = batch.NAMESPACE, capture.NAMESPACE, list(sys.path)
    original_spec = importlib.util.spec_from_file_location

    def fixture_spec(name, location, *args, **kwargs):
        if Path(location).absolute() == PRIVATE_OWNER:
            intercepted.append(str(PRIVATE_OWNER))
            return importlib.machinery.ModuleSpec(
                name, InventedOwnerLoader(), origin="invented-owner-no-file"
            )
        return original_spec(name, location, *args, **kwargs)

    monkeypatch.setattr(importlib.util, "spec_from_file_location", fixture_spec)
    try:
        spec = original_spec("invented_" + script.stem, script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert intercepted == [str(PRIVATE_OWNER)]
        assert private_reads == []
        assert module.owner.fixture_origin == "invented_no_private_source"
        folder = tmp_path / "invented-only"
        folder.mkdir(mode=0o700)
        monkeypatch.setattr(module, "FOLDER", folder)
        monkeypatch.setattr(module, "MODULE", folder / "control_worker.py")
        monkeypatch.setattr(module, "ROOT", tmp_path)
        module.fixture_private_reads = private_reads
        module.fixture_intercepted_owner_imports = intercepted
        yield module
    finally:
        batch.NAMESPACE, capture.NAMESPACE = before[:2]
        sys.path[:] = before[2]
