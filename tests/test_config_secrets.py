"""回归测试：config.py 中密钥自动生成与 BOOTSTRAP_ADMIN_* 字段。

核心目标：
1. Settings 在无任何配置（ENCRYPTION_KEY/JWT_SECRET 为空）时仍可正常实例化。
2. 自动生成的密钥是非空字符串，且可被 crypto 模块使用。
3. BOOTSTRAP_ADMIN_* 字段存在且具有正确默认值（修复 AttributeError 回归）。
4. 显式设置的密钥不被覆盖。
5. 空 DATABASE_URL 正确保留（由 database.py 降级为 SQLite）。
"""

import builtins
import hashlib
import io
import logging
import os
import stat
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest


_FICTIONAL_ENCRYPTION_KEY = "fictional-encryption-key-for-f009-only"
_FICTIONAL_JWT_SECRET = "fictional-jwt-secret-for-f009-only"
_ENVIRONMENT_ENCRYPTION_KEY = "fictional-environment-encryption-key"
_ENVIRONMENT_JWT_SECRET = "fictional-environment-jwt-secret"
_GENERATED_ENCRYPTION_SENTINEL = "generated-encryption-sentinel-must-not-leak"
_GENERATED_JWT_SENTINEL = "generated-jwt-sentinel-must-not-leak"

_ENV_OVERRIDE_CASES = (
    pytest.param({}, id="file-keys"),
    pytest.param(
        {
            "ENCRYPTION_KEY": _ENVIRONMENT_ENCRYPTION_KEY,
            "JWT_SECRET": _ENVIRONMENT_JWT_SECRET,
        },
        id="environment-keys",
    ),
)
_KEY_SOURCE_CASES = (
    pytest.param({}, True, id="file-keys"),
    pytest.param(
        {
            "ENCRYPTION_KEY": _ENVIRONMENT_ENCRYPTION_KEY,
            "JWT_SECRET": _ENVIRONMENT_JWT_SECRET,
        },
        False,
        id="environment-keys",
    ),
)


def _secret_file_body() -> str:
    return (
        f"ENCRYPTION_KEY={_FICTIONAL_ENCRYPTION_KEY}\n"
        f"JWT_SECRET={_FICTIONAL_JWT_SECRET}\n"
    )


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.lstat().st_mode)


def _same_reference(reference, path: Path) -> bool:
    try:
        if isinstance(reference, int):
            return os.path.samestat(os.fstat(reference), path.stat())
        return Path(reference).absolute() == path.absolute()
    except (OSError, TypeError, ValueError):
        return False


def _install_content_read_probe(monkeypatch, path: Path) -> list[tuple[str, int]]:
    """记录成功正文读取边界及其 fd mode，不阻止安全元数据检查。"""
    observations: list[tuple[str, int]] = []
    real_io_open = io.open
    real_builtin_open = builtins.open
    real_os_read = os.read

    def observed_stream_open(real_open, operation: str):
        def _open(file, mode="r", *args, **kwargs):
            stream = real_open(file, mode, *args, **kwargs)
            if "r" in str(mode) and (
                _same_reference(file, path) or _same_reference(stream.fileno(), path)
            ):
                observations.append(
                    (operation, stat.S_IMODE(os.fstat(stream.fileno()).st_mode))
                )
            return stream

        return _open

    def observed_os_read(fd, length):
        if _same_reference(fd, path):
            observations.append(("os.read", stat.S_IMODE(os.fstat(fd).st_mode)))
        return real_os_read(fd, length)

    monkeypatch.setattr(io, "open", observed_stream_open(real_io_open, "io.open"))
    monkeypatch.setattr(
        builtins,
        "open",
        observed_stream_open(real_builtin_open, "builtins.open"),
    )
    monkeypatch.setattr(os, "read", observed_os_read)
    return observations


def _is_write_access(mode_or_flags) -> bool:
    if isinstance(mode_or_flags, int):
        write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC
        return bool(mode_or_flags & write_flags)
    return any(flag in str(mode_or_flags) for flag in "wax+")


class _FailingWriteStream:
    """保留真实打开/关闭行为，但在第一次正文写入时失败。"""

    def __init__(self, stream):
        self._stream = stream

    def __enter__(self):
        self._stream.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self._stream.__exit__(exc_type, exc_value, traceback)

    def __getattr__(self, name):
        return getattr(self._stream, name)

    def write(self, _data):
        raise PermissionError("fictional secure write failure")

    def writelines(self, _lines):
        raise PermissionError("fictional secure write failure")


def _install_after_open_write_failure(monkeypatch) -> None:
    """允许安全打开，再在 Settings 期间的第一笔正文写入处失败。"""
    real_io_open = io.open
    real_builtin_open = builtins.open

    def failing_stream_open(real_open):
        def _open(file, mode="r", *args, **kwargs):
            stream = real_open(file, mode, *args, **kwargs)
            if _is_write_access(mode):
                return _FailingWriteStream(stream)
            return stream

        return _open

    def denied_os_write(_fd, _data):
        raise PermissionError("fictional secure write failure")

    monkeypatch.setattr(io, "open", failing_stream_open(real_io_open))
    monkeypatch.setattr(
        builtins,
        "open",
        failing_stream_open(real_builtin_open),
    )
    monkeypatch.setattr(os, "write", denied_os_write)


def _capture_settings_error(**env_overrides):
    try:
        _make_settings(**env_overrides)
    except Exception as exc:  # noqa: BLE001 - public contract is fail-closed, not an exception type
        return exc
    return None


def _assert_failure_is_sanitized(error, caplog, *sensitive_values: str) -> None:
    persistence_success_records = [
        record
        for record in caplog.records
        if record.name == "app.config" and record.levelno == logging.INFO
    ]
    assert persistence_success_records == []
    assert error is not None
    rendered_error = str(error)
    rendered_logs = "\n".join(record.getMessage() for record in caplog.records)
    for value in sensitive_values:
        assert value not in rendered_error
        assert value not in rendered_logs


def _make_settings(**env_overrides):
    """在受控环境下构造 Settings 实例，不读取磁盘 .env 文件。"""
    from pydantic_settings import SettingsConfigDict
    from app.core import config as config_mod

    class _IsolatedSettings(config_mod.Settings):
        # 覆盖 env_file，让测试不读取项目 .env
        model_config = SettingsConfigDict(
            env_file=None,
            env_file_encoding="utf-8",
            extra="ignore",
        )

    # 清除可能被 monkeypatch 残留的环境变量
    env = {
        k: v
        for k, v in os.environ.items()
        if k
        not in {
            "DATABASE_URL",
            "ENCRYPTION_KEY",
            "JWT_SECRET",
            "HOLIDAY_API_URL",
            "BOOTSTRAP_ADMIN_ENABLED",
            "BOOTSTRAP_ADMIN_TENANT_ID",
            "BOOTSTRAP_ADMIN_USERNAME",
            "BOOTSTRAP_ADMIN_PASSWORD",
            "BOOTSTRAP_ADMIN_ALLOW_REMOTE",
        }
    }
    env.update({k: str(v) for k, v in env_overrides.items()})

    old_env = os.environ.copy()
    os.environ.clear()
    os.environ.update(env)
    try:
        return _IsolatedSettings()
    finally:
        os.environ.clear()
        os.environ.update(old_env)


def test_settings_reads_env_file_from_explicit_data_dir(
    tmp_path: Path, monkeypatch
) -> None:
    """显式数据目录下的 .env 必须同时成为 Settings 的配置来源。"""
    from app.core import config as config_mod
    from app.core import env_writer

    working_dir = tmp_path / "source-cwd"
    data_dir = tmp_path / "runtime-data"
    working_dir.mkdir()
    monkeypatch.chdir(working_dir)
    monkeypatch.setenv("KINDERGARTEN_DATA_DIR", str(data_dir))
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.setenv("ENCRYPTION_KEY", _ENVIRONMENT_ENCRYPTION_KEY)
    monkeypatch.setenv("JWT_SECRET", _ENVIRONMENT_JWT_SECRET)

    (working_dir / ".env").write_text(
        "PORT=41000\nLOG_LEVEL=WARNING\n",
        encoding="utf-8",
    )
    env_writer.write_dot_env({"PORT": "49173", "LOG_LEVEL": "DEBUG"})
    env_path = data_dir / ".env"
    assert env_writer.get_env_path() == env_path

    settings = config_mod.Settings()

    assert settings.PORT == 49173
    assert settings.LOG_LEVEL == "DEBUG"

    monkeypatch.setenv("PORT", "49174")
    overridden = config_mod.Settings()
    assert overridden.PORT == 49174
    assert overridden.LOG_LEVEL == "DEBUG"


def test_settings_rejects_symlinked_env_in_explicit_data_dir(
    tmp_path: Path, monkeypatch
) -> None:
    """Settings 不得绕过 env_writer 的非跟随校验读取 symlink 配置。"""
    if os.name != "posix":
        pytest.skip("POSIX symlink contract")

    from app.core import config as config_mod

    data_dir = tmp_path / "runtime-data"
    data_dir.mkdir(mode=0o700)
    victim = tmp_path / "untrusted.env"
    victim.write_text("PORT=49175\n", encoding="utf-8")
    (data_dir / ".env").symlink_to(victim)
    monkeypatch.setenv("KINDERGARTEN_DATA_DIR", str(data_dir))
    monkeypatch.setenv("ENCRYPTION_KEY", _ENVIRONMENT_ENCRYPTION_KEY)
    monkeypatch.setenv("JWT_SECRET", _ENVIRONMENT_JWT_SECRET)

    with pytest.raises(RuntimeError, match="配置文件"):
        config_mod.Settings()


def test_settings_loads_the_same_secure_env_snapshot_after_path_swap(
    tmp_path: Path, monkeypatch
) -> None:
    """安全读取后路径被替换时，Settings 不得二次按路径打开攻击者文件。"""
    if os.name != "posix":
        pytest.skip("POSIX path-swap contract")

    from app.core import config as config_mod
    from app.core import env_writer

    data_dir = tmp_path / "runtime-data"
    data_dir.mkdir(mode=0o700)
    env_path = data_dir / ".env"
    env_path.write_text("PORT=49173\n", encoding="utf-8")
    attacker_file = tmp_path / "attacker.env"
    attacker_file.write_text("PORT=49175\n", encoding="utf-8")
    monkeypatch.setenv("KINDERGARTEN_DATA_DIR", str(data_dir))
    monkeypatch.setenv("ENCRYPTION_KEY", _ENVIRONMENT_ENCRYPTION_KEY)
    monkeypatch.setenv("JWT_SECRET", _ENVIRONMENT_JWT_SECRET)
    monkeypatch.delenv("PORT", raising=False)

    secure_read = env_writer._read_posix_text

    def _read_then_swap(path: Path) -> str | None:
        snapshot = secure_read(path)
        path.unlink()
        path.symlink_to(attacker_file)
        return snapshot

    monkeypatch.setattr(env_writer, "_read_posix_text", _read_then_swap)

    settings = config_mod.Settings()

    assert settings.PORT == 49173


def test_settings_preserves_subclass_explicit_env_file(
    tmp_path: Path, monkeypatch
) -> None:
    """显式 subclass dotenv source 不得被应用默认数据目录覆盖。"""
    from pydantic_settings import SettingsConfigDict

    from app.core import config as config_mod

    custom_env = tmp_path / "custom.env"
    custom_env.write_text("PORT=49176\n", encoding="utf-8")
    data_dir = tmp_path / "runtime-data"
    monkeypatch.setenv("KINDERGARTEN_DATA_DIR", str(data_dir))
    monkeypatch.setenv("ENCRYPTION_KEY", _ENVIRONMENT_ENCRYPTION_KEY)
    monkeypatch.setenv("JWT_SECRET", _ENVIRONMENT_JWT_SECRET)
    monkeypatch.delenv("PORT", raising=False)

    class _CustomEnvSettings(config_mod.Settings):
        model_config = SettingsConfigDict(
            env_file=custom_env,
            env_file_encoding="utf-8",
            extra="ignore",
        )

    assert _CustomEnvSettings().PORT == 49176


def _assert_non_posix_regular_file_contract(tmp_path, monkeypatch) -> None:
    """只验证跨平台功能，不把 POSIX mode 当作 Windows DACL 证据。"""
    secrets_path = tmp_path / ".kindergarten_secrets"
    secrets_path.write_text(_secret_file_body(), encoding="utf-8")
    digest_before = _file_digest(secrets_path)
    monkeypatch.setattr("app.core.config._secrets_file_path", lambda: secrets_path)

    file_settings = _make_settings()

    assert file_settings.ENCRYPTION_KEY == _FICTIONAL_ENCRYPTION_KEY
    assert file_settings.JWT_SECRET == _FICTIONAL_JWT_SECRET
    assert _file_digest(secrets_path) == digest_before

    environment_settings = _make_settings(
        ENCRYPTION_KEY=_ENVIRONMENT_ENCRYPTION_KEY,
        JWT_SECRET=_ENVIRONMENT_JWT_SECRET,
    )

    assert environment_settings.ENCRYPTION_KEY == _ENVIRONMENT_ENCRYPTION_KEY
    assert environment_settings.JWT_SECRET == _ENVIRONMENT_JWT_SECRET
    assert _file_digest(secrets_path) == digest_before


def test_settings_instantiates_with_no_config(tmp_path, monkeypatch):
    """无任何配置时，Settings() 应成功实例化（修复必填字段导致的启动崩溃）。"""
    monkeypatch.setattr(
        "app.core.config._secrets_file_path", lambda: tmp_path / ".kindergarten_secrets"
    )

    s = _make_settings()

    assert isinstance(s.ENCRYPTION_KEY, str) and len(s.ENCRYPTION_KEY) > 0
    assert isinstance(s.JWT_SECRET, str) and len(s.JWT_SECRET) > 0


def test_empty_encryption_key_auto_generates(tmp_path, monkeypatch):
    """ENCRYPTION_KEY 为空时应自动生成非空值。"""
    monkeypatch.setattr(
        "app.core.config._secrets_file_path", lambda: tmp_path / ".kindergarten_secrets"
    )

    s = _make_settings()

    assert s.ENCRYPTION_KEY
    assert len(s.ENCRYPTION_KEY) >= 20  # token_urlsafe(32) => 43 chars


def test_empty_jwt_secret_auto_generates(tmp_path, monkeypatch):
    """JWT_SECRET 为空时应自动生成非空值。"""
    monkeypatch.setattr(
        "app.core.config._secrets_file_path", lambda: tmp_path / ".kindergarten_secrets"
    )

    s = _make_settings()

    assert s.JWT_SECRET
    assert len(s.JWT_SECRET) >= 20  # token_urlsafe(64) => 86 chars


def test_explicit_encryption_key_not_overwritten(tmp_path, monkeypatch):
    """已设置的 ENCRYPTION_KEY 不应被自动生成逻辑覆盖。"""
    monkeypatch.setattr(
        "app.core.config._secrets_file_path", lambda: tmp_path / ".kindergarten_secrets"
    )
    fixed_key = "my-fixed-key-for-testing-only-32b"

    s = _make_settings(ENCRYPTION_KEY=fixed_key, JWT_SECRET="fixed-jwt-secret-for-test")

    assert s.ENCRYPTION_KEY == fixed_key


def test_auto_generated_key_persisted_and_reused(tmp_path, monkeypatch):
    """首次生成的密钥写入持久化文件，第二次实例化时读回相同值。"""
    secrets_path = tmp_path / ".kindergarten_secrets"
    monkeypatch.setattr("app.core.config._secrets_file_path", lambda: secrets_path)

    s1 = _make_settings()
    key1 = s1.ENCRYPTION_KEY
    jwt1 = s1.JWT_SECRET

    assert secrets_path.exists(), "持久化文件应被创建"

    s2 = _make_settings()
    assert s2.ENCRYPTION_KEY == key1, "重启后应读回相同的 ENCRYPTION_KEY"
    assert s2.JWT_SECRET == jwt1, "重启后应读回相同的 JWT_SECRET"


def test_auto_generated_key_usable_by_crypto(tmp_path, monkeypatch):
    """自动生成的 ENCRYPTION_KEY 应能被 app.core.crypto 正常使用。"""
    monkeypatch.setattr(
        "app.core.config._secrets_file_path", lambda: tmp_path / ".kindergarten_secrets"
    )

    s = _make_settings()

    # 动态构造使用生成密钥的 Fernet 加密器（不污染全局 settings）
    import base64
    from cryptography.fernet import Fernet

    raw = s.ENCRYPTION_KEY.encode("utf-8")[:32].ljust(32, b"\x00")
    fernet_key = base64.urlsafe_b64encode(raw)
    f = Fernet(fernet_key)
    cipher = f.encrypt(b"hello")
    assert f.decrypt(cipher) == b"hello"


# ── F009：密钥持久化文件必须 fail-closed 且 POSIX owner-only ────────────────


def test_new_secrets_file_is_owner_only_from_creation_with_permissive_umask(
    tmp_path, monkeypatch
):
    """POSIX 新文件即使在 umask=0 下也不得短暂暴露为 group/other 可读。"""
    secrets_path = tmp_path / ".kindergarten_secrets"
    monkeypatch.setattr("app.core.config._secrets_file_path", lambda: secrets_path)

    if os.name != "posix":
        settings = _make_settings()
        assert secrets_path.is_file()
        assert settings.ENCRYPTION_KEY and settings.JWT_SECRET
        _assert_non_posix_regular_file_contract(tmp_path, monkeypatch)
        return

    creation_modes: list[int] = []
    pre_correction_modes: list[int] = []
    real_os_open = os.open
    real_io_open = io.open
    real_builtin_open = builtins.open
    real_chmod = os.chmod
    real_fchmod = os.fchmod

    def observed_os_open(path, flags, mode=0o777, *args, **kwargs):
        did_exist = secrets_path.exists()
        fd = real_os_open(path, flags, mode, *args, **kwargs)
        if not did_exist and flags & os.O_CREAT and _same_reference(fd, secrets_path):
            creation_modes.append(stat.S_IMODE(os.fstat(fd).st_mode))
        return fd

    def observed_stream_open(real_open):
        def _open(file, mode="r", *args, **kwargs):
            did_exist = secrets_path.exists()
            stream = real_open(file, mode, *args, **kwargs)
            if (
                not did_exist
                and any(flag in str(mode) for flag in "wax+")
                and _same_reference(stream.fileno(), secrets_path)
            ):
                creation_modes.append(stat.S_IMODE(os.fstat(stream.fileno()).st_mode))
            return stream

        return _open

    def observed_chmod(path, mode, *args, **kwargs):
        if _same_reference(path, secrets_path):
            pre_correction_modes.append(_mode(secrets_path))
        return real_chmod(path, mode, *args, **kwargs)

    def observed_fchmod(fd, mode):
        if _same_reference(fd, secrets_path):
            pre_correction_modes.append(stat.S_IMODE(os.fstat(fd).st_mode))
        return real_fchmod(fd, mode)

    monkeypatch.setattr(os, "open", observed_os_open)
    monkeypatch.setattr(io, "open", observed_stream_open(real_io_open))
    monkeypatch.setattr(builtins, "open", observed_stream_open(real_builtin_open))
    monkeypatch.setattr(os, "chmod", observed_chmod)
    monkeypatch.setattr(os, "fchmod", observed_fchmod)

    previous_umask = os.umask(0)
    try:
        settings = _make_settings()
    finally:
        os.umask(previous_umask)

    assert settings.ENCRYPTION_KEY and settings.JWT_SECRET
    assert creation_modes, "测试必须观测到密钥文件的创建时权限"
    assert all(mode == 0o600 for mode in creation_modes)
    assert all(mode == 0o600 for mode in pre_correction_modes)
    assert _mode(secrets_path) == 0o600


@pytest.mark.parametrize(
    ("env_overrides", "must_read_file"),
    _KEY_SOURCE_CASES,
)
def test_existing_secrets_are_owner_only_before_first_read_without_content_change(
    tmp_path,
    monkeypatch,
    env_overrides,
    must_read_file,
):
    """既有 0664 普通文件必须先纠权再读，且不得重写其正文。"""
    secrets_path = tmp_path / ".kindergarten_secrets"
    secrets_path.write_text(_secret_file_body(), encoding="utf-8")
    digest_before = _file_digest(secrets_path)
    monkeypatch.setattr("app.core.config._secrets_file_path", lambda: secrets_path)

    read_observations: list[tuple[str, int]] = []
    if os.name == "posix":
        secrets_path.chmod(0o664)
        read_observations = _install_content_read_probe(
            monkeypatch,
            secrets_path,
        )

    settings = _make_settings(**env_overrides)

    if os.name == "posix":
        if must_read_file:
            assert read_observations, "文件 Key 必须经过受监测的正文读取边界"
        assert all(mode == 0o600 for _, mode in read_observations)
        assert _mode(secrets_path) == 0o600
    assert _file_digest(secrets_path) == digest_before
    expected_encryption_key = env_overrides.get(
        "ENCRYPTION_KEY",
        _FICTIONAL_ENCRYPTION_KEY,
    )
    expected_jwt_secret = env_overrides.get(
        "JWT_SECRET",
        _FICTIONAL_JWT_SECRET,
    )
    assert settings.ENCRYPTION_KEY == expected_encryption_key
    assert settings.JWT_SECRET == expected_jwt_secret


def test_concurrent_settings_initialization_returns_only_persisted_secret_pair(
    tmp_path,
    monkeypatch,
):
    """并发启动都只能返回同一组已持久化密钥，不能各自成功后丢失一组。"""
    if os.name != "posix":
        _assert_non_posix_regular_file_contract(tmp_path, monkeypatch)
        return

    from pydantic_settings import SettingsConfigDict
    from app.core import config as config_mod

    secrets_path = tmp_path / ".kindergarten_secrets"
    secrets_path.write_text("F009_CONCURRENCY_SENTINEL=preserved\n", encoding="utf-8")
    secrets_path.chmod(0o600)
    monkeypatch.setattr("app.core.config._secrets_file_path", lambda: secrets_path)

    ready = threading.Barrier(3)
    start = threading.Event()
    generation_gate = threading.Barrier(2)

    def generated_token(size: int) -> str:
        # 当前无锁实现的两个构造会在这里确定性交错。未来正确实现必须用跨进程
        # 文件锁覆盖 read→generate→persist 全过程，不能只加进程内线程锁。
        # 锁内首个参与者会超时降级，随后参与者应直接复用落盘值，避免测试死锁。
        if size == 32:
            try:
                generation_gate.wait(timeout=1)
            except threading.BrokenBarrierError:
                pass
        return f"generated-{size}-{threading.current_thread().name}"

    monkeypatch.setattr(
        "app.core.config.secrets.token_urlsafe",
        generated_token,
    )

    class _ConcurrentSettings(config_mod.Settings):
        model_config = SettingsConfigDict(
            env_file=None,
            env_file_encoding="utf-8",
            extra="ignore",
        )

    def construct_settings() -> config_mod.Settings:
        ready.wait(timeout=2)
        assert start.wait(timeout=2)
        return _ConcurrentSettings(ENCRYPTION_KEY="", JWT_SECRET="")

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="f009-writer") as pool:
        futures = [pool.submit(construct_settings) for _ in range(2)]
        ready.wait(timeout=2)
        start.set()
        constructed = [future.result(timeout=5) for future in futures]

    returned_pairs = {
        (settings.ENCRYPTION_KEY, settings.JWT_SECRET) for settings in constructed
    }
    persisted = {
        key: value
        for line in secrets_path.read_text(encoding="utf-8").splitlines()
        if (key_value := line.partition("="))[1]
        for key, value in ((key_value[0], key_value[2]),)
    }

    assert len(returned_pairs) == 1
    assert returned_pairs == {
        (persisted["ENCRYPTION_KEY"], persisted["JWT_SECRET"]),
    }
    assert persisted["F009_CONCURRENCY_SENTINEL"] == "preserved"


@pytest.mark.parametrize("env_overrides", _ENV_OVERRIDE_CASES)
def test_secrets_symlink_is_rejected_without_reading_target(
    tmp_path,
    monkeypatch,
    caplog,
    env_overrides,
):
    """密钥路径为 symlink 时必须拒绝，不能跟随到目标文件。"""
    if os.name != "posix":
        _assert_non_posix_regular_file_contract(tmp_path, monkeypatch)
        return

    target = tmp_path / "fictional-target"
    target.write_text(_secret_file_body(), encoding="utf-8")
    target.chmod(0o600)
    digest_before = _file_digest(target)
    secrets_path = tmp_path / ".kindergarten_secrets"
    secrets_path.symlink_to(target)
    monkeypatch.setattr("app.core.config._secrets_file_path", lambda: secrets_path)
    read_observations = _install_content_read_probe(monkeypatch, secrets_path)
    caplog.set_level(logging.INFO, logger="app.config")

    error = _capture_settings_error(**env_overrides)

    _assert_failure_is_sanitized(
        error,
        caplog,
        _FICTIONAL_ENCRYPTION_KEY,
        _FICTIONAL_JWT_SECRET,
        *env_overrides.values(),
    )
    assert read_observations == []
    assert secrets_path.is_symlink()
    assert _file_digest(target) == digest_before


@pytest.mark.parametrize("env_overrides", _ENV_OVERRIDE_CASES)
def test_secrets_fifo_is_rejected_without_blocking_or_reading(
    tmp_path,
    monkeypatch,
    caplog,
    env_overrides,
):
    """FIFO 必须以 non-blocking 方式打开并在任何正文读取前拒绝。"""
    if os.name != "posix":
        _assert_non_posix_regular_file_contract(tmp_path, monkeypatch)
        return

    secrets_path = tmp_path / ".kindergarten_secrets"
    os.mkfifo(secrets_path, 0o600)
    monkeypatch.setattr("app.core.config._secrets_file_path", lambda: secrets_path)
    read_observations = _install_content_read_probe(monkeypatch, secrets_path)
    target_open_flags: list[int] = []
    real_os_open = os.open
    blocking_open_sentinel = "fictional FIFO blocking open must not leak"

    def require_nonblocking_open(path, flags, mode=0o777, *args, **kwargs):
        if _same_reference(path, secrets_path):
            target_open_flags.append(flags)
            if not flags & os.O_NONBLOCK:
                raise OSError(blocking_open_sentinel)
        return real_os_open(path, flags, mode, *args, **kwargs)

    monkeypatch.setattr(os, "open", require_nonblocking_open)
    caplog.set_level(logging.INFO, logger="app.config")

    error = _capture_settings_error(**env_overrides)

    _assert_failure_is_sanitized(
        error,
        caplog,
        blocking_open_sentinel,
        *env_overrides.values(),
    )
    assert target_open_flags, "测试必须观测到密钥 FIFO 的安全打开边界"
    assert all(flags & os.O_NONBLOCK for flags in target_open_flags)
    assert read_observations == []
    assert stat.S_ISFIFO(secrets_path.lstat().st_mode)


@pytest.mark.parametrize("env_overrides", _ENV_OVERRIDE_CASES)
def test_non_regular_secrets_path_is_rejected(
    tmp_path,
    monkeypatch,
    caplog,
    env_overrides,
):
    """目录等非普通文件不得被当作缺失配置后继续启动。"""
    secrets_path = tmp_path / ".kindergarten_secrets"
    secrets_path.mkdir()
    monkeypatch.setattr("app.core.config._secrets_file_path", lambda: secrets_path)
    caplog.set_level(logging.INFO, logger="app.config")

    error = _capture_settings_error(**env_overrides)

    _assert_failure_is_sanitized(error, caplog, *env_overrides.values())


@pytest.mark.parametrize("env_overrides", _ENV_OVERRIDE_CASES)
def test_permission_correction_failure_is_fail_closed(
    tmp_path,
    monkeypatch,
    caplog,
    env_overrides,
):
    """既有文件无法纠权时必须停止，且不得读取正文或宣称已持久化。"""
    if os.name != "posix":
        _assert_non_posix_regular_file_contract(tmp_path, monkeypatch)
        return

    secrets_path = tmp_path / ".kindergarten_secrets"
    secrets_path.write_text(_secret_file_body(), encoding="utf-8")
    secrets_path.chmod(0o664)
    digest_before = _file_digest(secrets_path)
    monkeypatch.setattr("app.core.config._secrets_file_path", lambda: secrets_path)
    real_chmod = os.chmod
    real_fchmod = os.fchmod

    def denied_chmod(path, mode, *args, **kwargs):
        if _same_reference(path, secrets_path):
            raise PermissionError("fictional permission correction failure")
        return real_chmod(path, mode, *args, **kwargs)

    def denied_fchmod(fd, mode):
        if _same_reference(fd, secrets_path):
            raise PermissionError("fictional permission correction failure")
        return real_fchmod(fd, mode)

    monkeypatch.setattr(os, "chmod", denied_chmod)
    monkeypatch.setattr(os, "fchmod", denied_fchmod)
    read_observations = _install_content_read_probe(monkeypatch, secrets_path)
    caplog.set_level(logging.INFO, logger="app.config")

    error = _capture_settings_error(**env_overrides)

    _assert_failure_is_sanitized(
        error,
        caplog,
        _FICTIONAL_ENCRYPTION_KEY,
        _FICTIONAL_JWT_SECRET,
        *env_overrides.values(),
    )
    assert read_observations == []
    assert _mode(secrets_path) == 0o664
    assert _file_digest(secrets_path) == digest_before


def test_secure_secrets_write_failure_is_fail_closed(tmp_path, monkeypatch, caplog):
    """生成的两个密钥写入失败时必须向上传播、清理并保持脱敏。"""
    secrets_path = tmp_path / ".kindergarten_secrets"
    monkeypatch.setattr("app.core.config._secrets_file_path", lambda: secrets_path)
    generated_values = iter((_GENERATED_ENCRYPTION_SENTINEL, _GENERATED_JWT_SENTINEL))
    generated_calls: list[int] = []

    def generated_token(size: int) -> str:
        generated_calls.append(size)
        return next(generated_values)

    monkeypatch.setattr(
        "app.core.config.secrets.token_urlsafe",
        generated_token,
    )
    _install_after_open_write_failure(monkeypatch)
    caplog.set_level(logging.INFO, logger="app.config")

    error = _capture_settings_error()

    assert len(generated_calls) == 2
    _assert_failure_is_sanitized(
        error,
        caplog,
        _GENERATED_ENCRYPTION_SENTINEL,
        _GENERATED_JWT_SENTINEL,
    )
    assert not secrets_path.exists()


def test_interrupted_initial_posix_write_removes_partial_file_and_propagates(
    tmp_path,
    monkeypatch,
    caplog,
):
    """首次创建被 BaseException 中断时不得遗留可被下次启动信任的残片。"""
    if os.name != "posix":
        _assert_non_posix_regular_file_contract(tmp_path, monkeypatch)
        return

    secrets_path = tmp_path / ".kindergarten_secrets"
    monkeypatch.setattr("app.core.config._secrets_file_path", lambda: secrets_path)
    generated_values = iter((_GENERATED_ENCRYPTION_SENTINEL, _GENERATED_JWT_SENTINEL))
    monkeypatch.setattr(
        "app.core.config.secrets.token_urlsafe",
        lambda _size: next(generated_values),
    )
    real_os_write = os.write
    interruption = KeyboardInterrupt("fictional interrupted secret creation")
    partial_write_sizes: list[int] = []

    def interrupt_after_partial_write(fd: int, payload: bytes) -> int:
        if _same_reference(fd, secrets_path):
            partial_size = max(1, len(payload) // 2)
            written = real_os_write(fd, payload[:partial_size])
            partial_write_sizes.append(written)
            raise interruption
        return real_os_write(fd, payload)

    monkeypatch.setattr(os, "write", interrupt_after_partial_write)
    caplog.set_level(logging.INFO, logger="app.config")

    with pytest.raises(KeyboardInterrupt) as captured:
        _make_settings()

    assert captured.value is interruption
    assert partial_write_sizes and all(size > 0 for size in partial_write_sizes)
    _assert_failure_is_sanitized(
        captured.value,
        caplog,
        _GENERATED_ENCRYPTION_SENTINEL,
        _GENERATED_JWT_SENTINEL,
    )
    assert not secrets_path.exists()


def test_interrupted_initial_identity_check_removes_empty_file_and_propagates(
    tmp_path,
    monkeypatch,
    caplog,
):
    """首次创建后的 identity 检查被中断时也必须清理最终路径。"""
    if os.name != "posix":
        _assert_non_posix_regular_file_contract(tmp_path, monkeypatch)
        return

    from app.core import config as config_mod

    secrets_path = tmp_path / ".kindergarten_secrets"
    monkeypatch.setattr("app.core.config._secrets_file_path", lambda: secrets_path)
    generated_values = iter((_GENERATED_ENCRYPTION_SENTINEL, _GENERATED_JWT_SENTINEL))
    monkeypatch.setattr(
        "app.core.config.secrets.token_urlsafe",
        lambda _size: next(generated_values),
    )
    real_regular_fd_identity = config_mod._regular_fd_identity
    interruption = KeyboardInterrupt("fictional interrupted identity check")
    target_identity_calls = 0

    def interrupt_first_identity_check(fd: int, path: Path):
        nonlocal target_identity_calls
        if path == secrets_path:
            target_identity_calls += 1
            if target_identity_calls == 1:
                raise interruption
        return real_regular_fd_identity(fd, path)

    monkeypatch.setattr(
        "app.core.config._regular_fd_identity",
        interrupt_first_identity_check,
    )
    caplog.set_level(logging.INFO, logger="app.config")

    with pytest.raises(KeyboardInterrupt) as captured:
        _make_settings()

    assert captured.value is interruption
    assert target_identity_calls == 2
    _assert_failure_is_sanitized(
        captured.value,
        caplog,
        _GENERATED_ENCRYPTION_SENTINEL,
        _GENERATED_JWT_SENTINEL,
    )
    assert not secrets_path.exists()


def test_existing_single_key_digest_survives_missing_key_write_failure(
    tmp_path,
    monkeypatch,
    caplog,
):
    """既有单 Key 的补写失败不得截断或改写原文件。"""
    secrets_path = tmp_path / ".kindergarten_secrets"
    secrets_path.write_text(
        f"ENCRYPTION_KEY={_FICTIONAL_ENCRYPTION_KEY}\n",
        encoding="utf-8",
    )
    if os.name == "posix":
        secrets_path.chmod(0o600)
    digest_before = _file_digest(secrets_path)
    monkeypatch.setattr(
        "app.core.config._secrets_file_path",
        lambda: secrets_path,
    )
    generated_calls: list[int] = []

    def generated_token(size: int) -> str:
        generated_calls.append(size)
        return _GENERATED_JWT_SENTINEL

    monkeypatch.setattr(
        "app.core.config.secrets.token_urlsafe",
        generated_token,
    )
    _install_after_open_write_failure(monkeypatch)
    caplog.set_level(logging.INFO, logger="app.config")

    error = _capture_settings_error()

    assert len(generated_calls) == 1
    _assert_failure_is_sanitized(
        error,
        caplog,
        _FICTIONAL_ENCRYPTION_KEY,
        _GENERATED_JWT_SENTINEL,
    )
    assert _file_digest(secrets_path) == digest_before
    if os.name == "posix":
        assert _mode(secrets_path) == 0o600


# ── BOOTSTRAP_ADMIN_* 属性存在性回归（修复 AttributeError） ──────────────────


def test_bootstrap_admin_enabled_default():
    """BOOTSTRAP_ADMIN_ENABLED 默认 False。"""
    from app.core.config import settings

    assert settings.BOOTSTRAP_ADMIN_ENABLED is False


def test_bootstrap_admin_tenant_id_default():
    """BOOTSTRAP_ADMIN_TENANT_ID 默认 1。"""
    from app.core.config import settings

    assert settings.BOOTSTRAP_ADMIN_TENANT_ID == 1


def test_bootstrap_admin_username_default():
    """BOOTSTRAP_ADMIN_USERNAME 默认 'sysadmin'。"""
    from app.core.config import settings

    assert settings.BOOTSTRAP_ADMIN_USERNAME == "sysadmin"


def test_bootstrap_admin_password_default():
    """BOOTSTRAP_ADMIN_PASSWORD 默认空字符串。"""
    from app.core.config import settings

    assert settings.BOOTSTRAP_ADMIN_PASSWORD == ""


def test_bootstrap_admin_allow_remote_default():
    """BOOTSTRAP_ADMIN_ALLOW_REMOTE 默认 False。"""
    from app.core.config import settings

    assert settings.BOOTSTRAP_ADMIN_ALLOW_REMOTE is False


def test_database_url_default_is_empty():
    """DATABASE_URL 默认空字符串（交由 database.py 降级为 SQLite）。"""
    # 这里读取全局 settings，它由项目 .env 或环境变量决定
    from app.core.config import Settings

    # 只验证默认值，不依赖 .env
    assert Settings.model_fields["DATABASE_URL"].default == ""


def test_holiday_api_url_has_default():
    """HOLIDAY_API_URL 有内置默认值，不强制要求 .env 配置。"""
    from app.core.config import Settings

    assert (
        Settings.model_fields["HOLIDAY_API_URL"].default
        == "https://timor.tech/api/holiday/info/"
    )
