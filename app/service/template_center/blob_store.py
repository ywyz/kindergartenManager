"""Owner-only content-addressed storage for validated template blobs."""

from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
import stat
import tempfile

from app.service.template_center.contracts import (
    BlobRef,
    TemplateCenterError,
    TemplateErrorCode,
)


def _storage_failed(error: BaseException | None = None) -> TemplateCenterError:
    failure = TemplateCenterError(TemplateErrorCode.STORAGE_FAILED)
    if error is not None:
        failure.__cause__ = error
    return failure


def _validate_digest(value: object) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise _storage_failed()
    return value


def _safe_directory(path: Path, *, create: bool) -> None:
    try:
        if create:
            try:
                path.mkdir(mode=0o700)
            except FileExistsError:
                pass
        metadata = path.lstat()
    except (FileNotFoundError, OSError) as error:
        raise _storage_failed(error) from error
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
        raise _storage_failed()
    if stat.S_IMODE(metadata.st_mode) != 0o700:
        raise _storage_failed()


class ContentAddressedTemplateBlobStore:
    """Store immutable blobs beneath one trusted, owner-only root."""

    __slots__ = ("_root",)

    def __init__(self, trusted_root: Path) -> None:
        if not isinstance(trusted_root, Path) or not trusted_root.is_absolute():
            raise _storage_failed()
        try:
            if trusted_root.exists() or trusted_root.is_symlink():
                _safe_directory(trusted_root, create=False)
            else:
                _safe_directory(trusted_root, create=True)
        except TemplateCenterError:
            raise
        except OSError as error:
            raise _storage_failed(error) from error
        self._root = trusted_root

    def _blob_path(self, content_sha256: str, *, create_shard: bool) -> Path:
        digest = _validate_digest(content_sha256)
        _safe_directory(self._root, create=False)
        shard = self._root / digest[:2]
        if shard.exists() or shard.is_symlink():
            _safe_directory(shard, create=False)
        elif create_shard:
            _safe_directory(shard, create=True)
        return shard / digest

    @staticmethod
    def _read_verified(path: Path, expected_sha256: str) -> bytes:
        try:
            metadata = path.lstat()
            if (
                not stat.S_ISREG(metadata.st_mode)
                or stat.S_ISLNK(metadata.st_mode)
                or stat.S_IMODE(metadata.st_mode) != 0o600
            ):
                raise _storage_failed()
            content = path.read_bytes()
        except TemplateCenterError:
            raise
        except OSError as error:
            raise _storage_failed(error) from error
        if sha256(content).hexdigest() != expected_sha256:
            raise _storage_failed()
        return content

    async def put_if_absent(self, content_sha256: str, content: bytes) -> BlobRef:
        digest = _validate_digest(content_sha256)
        if type(content) is not bytes or sha256(content).hexdigest() != digest:
            raise _storage_failed()
        path = self._blob_path(digest, create_shard=True)
        if path.exists() or path.is_symlink():
            if self._read_verified(path, digest) != content:
                raise _storage_failed()
            return BlobRef(value=f"sha256/{digest}", content_sha256=digest)

        descriptor = -1
        temporary_name: str | None = None
        try:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=".template-blob-", dir=path.parent
            )
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb", closefd=True) as handle:
                descriptor = -1
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temporary_name, path)
            except FileExistsError:
                if self._read_verified(path, digest) != content:
                    raise _storage_failed()
            directory_descriptor = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        except TemplateCenterError:
            raise
        except OSError as error:
            raise _storage_failed(error) from error
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            if temporary_name is not None:
                try:
                    os.unlink(temporary_name)
                except FileNotFoundError:
                    pass
                except OSError:
                    pass
        return BlobRef(value=f"sha256/{digest}", content_sha256=digest)

    async def read(self, blob_ref: BlobRef, expected_sha256: str) -> bytes:
        digest = _validate_digest(expected_sha256)
        if (
            type(blob_ref) is not BlobRef
            or blob_ref.content_sha256 != digest
            or blob_ref.value != f"sha256/{digest}"
        ):
            raise _storage_failed()
        return self._read_verified(self._blob_path(digest, create_shard=False), digest)

    async def exists(self, blob_ref: BlobRef, expected_sha256: str) -> bool:
        digest = _validate_digest(expected_sha256)
        if (
            type(blob_ref) is not BlobRef
            or blob_ref.content_sha256 != digest
            or blob_ref.value != f"sha256/{digest}"
        ):
            raise _storage_failed()
        path = self._blob_path(digest, create_shard=False)
        if not path.exists() and not path.is_symlink():
            return False
        self._read_verified(path, digest)
        return True
