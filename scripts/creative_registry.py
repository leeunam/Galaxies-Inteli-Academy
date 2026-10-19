"""Private local registry; untrusted media paths never reach the analysis tool."""

from __future__ import annotations

import errno
import fcntl
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from pydantic import Field, ValidationError

from scripts.creative_contracts import (
    CampaignId,
    Contract,
    CreativeId,
    RegisteredCreative,
    RegistrationRequest,
    Sector,
    error_response,
)
from scripts.creative_media import CreativeError, inspect_media


class MediaRecord(Contract):
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)
    duration_seconds: float = Field(gt=0, le=60)
    width: int = Field(gt=0, le=1080)
    height: int = Field(gt=0, le=1920)


class CreativeRecord(Contract):
    campaign_id: CampaignId
    sector: Sector
    relative_path: str
    media: MediaRecord


class RegistryState(Contract):
    version: str = Field(pattern=r"^creative-registry-v1$")
    creatives: dict[CreativeId, CreativeRecord]


class CreativeRegistry:
    def __init__(self, uploads_root: Path, registry_file: Path):
        # These two locations are trusted operator configuration, never tool arguments.
        self.uploads_root = Path(uploads_root).absolute()
        self.registry_file = Path(registry_file).absolute()

    @contextmanager
    def open_media(self, relative_path: str):
        parts = Path(relative_path).parts
        if (
            not parts
            or Path(relative_path).is_absolute()
            or ".." in parts
            or ":" in relative_path
            or "\\" in relative_path
        ):
            raise CreativeError("unsafe_path")
        descriptors = []
        try:
            descriptors.append(
                os.open(self.uploads_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            )
            for part in parts[:-1]:
                descriptors.append(
                    os.open(
                        part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptors[-1]
                    )
                )
            fd = os.open(
                parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptors[-1]
            )
            with os.fdopen(fd, "rb") as handle:
                if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                    raise CreativeError("invalid_media")
                if Path(relative_path).suffix.lower() not in {".mp4", ".mov", ".webm"}:
                    raise CreativeError("invalid_media")
                yield handle
        except OSError as exc:
            code = "media_missing" if exc.errno == errno.ENOENT else "unsafe_path"
            raise CreativeError(code) from None
        finally:
            for fd in reversed(descriptors):
                os.close(fd)

    @contextmanager
    def _locked(self):
        try:
            self.registry_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            fd = os.open(
                self.registry_file.with_suffix(".lock"),
                os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK,
                0o600,
            )
            with os.fdopen(fd, "a+") as handle:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                try:
                    yield
                finally:
                    fcntl.flock(handle, fcntl.LOCK_UN)
        except (OSError, ValidationError, ValueError):
            raise CreativeError("registry_unavailable") from None

    def _load(self) -> RegistryState:
        try:
            fd = os.open(self.registry_file, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except FileNotFoundError:
            return RegistryState(version="creative-registry-v1", creatives={})
        with os.fdopen(fd, "rb") as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise CreativeError("registry_unavailable")
            raw = handle.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024:
            raise CreativeError("registry_unavailable")
        return RegistryState.model_validate_json(raw)

    def _save(self, state: RegistryState):
        path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", dir=self.registry_file.parent, delete=False, suffix=".tmp"
            ) as handle:
                path = Path(handle.name)
                handle.write(state.model_dump_json())
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(path, self.registry_file)
        finally:
            if path is not None:
                path.unlink(missing_ok=True)

    def register(self, payload: object) -> dict:
        try:
            request = RegistrationRequest.model_validate(payload)
        except ValidationError:
            return error_response("invalid_request")
        try:
            with self.open_media(request.relative_path) as handle:
                media = MediaRecord.model_validate(inspect_media(handle))
            creative_id = "cr_" + uuid4().hex
            with self._locked():
                state = self._load()
                state.creatives[creative_id] = CreativeRecord(
                    campaign_id=request.campaign_id,
                    sector=request.sector,
                    relative_path=request.relative_path,
                    media=media,
                )
                self._save(state)
            return RegisteredCreative(
                creative_id=creative_id, campaign_id=request.campaign_id, sector=request.sector
            ).model_dump(mode="json")
        except CreativeError as exc:
            return error_response(exc.code)
        except (OSError, ValidationError, ValueError):
            return error_response("registry_unavailable")

    def validate_creatives(self, request):
        with self._locked():
            state = self._load()
        for creative_id in request.creative_ids:
            record = state.creatives.get(creative_id)
            if record is None:
                raise CreativeError("unknown_creative")
            if record.campaign_id != request.campaign_id:
                raise CreativeError("campaign_mismatch")
            if record.sector != request.sector:
                raise CreativeError("sector_mismatch")
            with self.open_media(record.relative_path) as handle:
                media = inspect_media(handle)
            if media != record.media.model_dump(mode="json"):
                raise CreativeError("media_changed")
        return {creative_id: state.creatives[creative_id] for creative_id in request.creative_ids}
