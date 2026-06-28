"""Phase B — 数据模型冒烟测试（ORM + SQLite in-memory）。

测试策略：
- 用 async_session fixture（SQLite 内存库 + Base.metadata.create_all）验证 ORM 模型定义正确性。
- 真实 MySQL 迁移脚本通过 `alembic upgrade head` 手动执行后人工核查。
"""
import pytest
from sqlalchemy.exc import IntegrityError


# ─── TB1：AiApiKey.key_type ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ai_key_default_key_type(async_session):
    """AiApiKey 不传 key_type 时默认为 'text'。"""
    from app.core.models.ai_key import AiApiKey

    key = AiApiKey(
        tenant_id=1,
        user_id=1,
        api_base_url="https://api.openai.com/v1",
        api_key_encrypted="ciphertext",
        model_name="gpt-4o-mini",
        is_active=True,
        key_type="text",
    )
    async_session.add(key)
    await async_session.commit()
    await async_session.refresh(key)

    assert key.key_type == "text"


@pytest.mark.asyncio
async def test_ai_key_vision_type(async_session):
    """AiApiKey 可保存 key_type='vision'，两类型独立存在。"""
    from app.core.models.ai_key import AiApiKey

    text_key = AiApiKey(
        tenant_id=1, user_id=1,
        api_base_url="https://api.openai.com/v1",
        api_key_encrypted="text_cipher",
        model_name="gpt-4o-mini",
        is_active=True,
        key_type="text",
    )
    vision_key = AiApiKey(
        tenant_id=1, user_id=1,
        api_base_url="https://api.openai.com/v1",
        api_key_encrypted="vision_cipher",
        model_name="gpt-4o",
        is_active=True,
        key_type="vision",
    )
    async_session.add_all([text_key, vision_key])
    await async_session.commit()

    assert text_key.id is not None
    assert vision_key.id is not None
    assert text_key.key_type == "text"
    assert vision_key.key_type == "vision"


# ─── TB2：User.display_name ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_user_display_name_nullable(async_session):
    """User.display_name 可为 None（可空）。"""
    from app.core.models.user import User, UserRole

    user = User(
        tenant_id=1,
        username="testuser",
        hashed_password="hash",
        role=UserRole.teacher,
        is_active=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    assert user.display_name is None


@pytest.mark.asyncio
async def test_user_display_name_updatable(async_session):
    """User.display_name 可更新为字符串。"""
    from app.core.models.user import User, UserRole

    user = User(
        tenant_id=1,
        username="teacher1",
        hashed_password="hash",
        role=UserRole.teacher,
        is_active=True,
    )
    async_session.add(user)
    await async_session.commit()

    user.display_name = "张老师"
    await async_session.commit()
    await async_session.refresh(user)

    assert user.display_name == "张老师"


# ─── TB3：game_observation 表 ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_game_observation_insertable(async_session):
    """GameObservation 可插入并按 id 查询。"""
    from datetime import date

    from app.core.models.game_observation import GameObservation

    obs = GameObservation(
        tenant_id=1,
        user_id=1,
        obs_date=date(2026, 6, 9),
        time_range="9:00-9:40",
        big_env="户外",
        game_area="建构区",
        grade="中班",
        class_name="阳光班",
        adult_count=2,
        child_count=8,
        child_names="小明、小红",
        child_age="4岁",
        observer="张老师",
    )
    async_session.add(obs)
    await async_session.commit()
    await async_session.refresh(obs)

    assert obs.id is not None
    assert obs.tenant_id == 1
    assert obs.big_env == "户外"


@pytest.mark.asyncio
async def test_game_observation_tenant_required(async_session):
    """GameObservation.tenant_id 非空约束生效。"""
    from sqlalchemy.exc import IntegrityError

    from app.core.models.game_observation import GameObservation

    obs = GameObservation(
        user_id=1,
        obs_date="2026-06-09",
        big_env="户外",
        game_area="建构区",
        grade="中班",
        class_name="阳光班",
    )
    async_session.add(obs)
    with pytest.raises((IntegrityError, Exception)):
        await async_session.commit()


# ─── TB4：game_observation_image blob ────────────────────────────────────────

@pytest.mark.asyncio
async def test_game_observation_image_blob_roundtrip(async_session):
    """GameObservationImage.blob_content 可存取二进制字节，值完全相同。"""
    from app.core.models.game_observation_image import GameObservationImage

    sample_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # 模拟小图二进制

    img = GameObservationImage(
        tenant_id=1,
        user_id=1,
        observation_id=999,
        image_index=1,
        storage_backend="mysql_blob",
        blob_content=sample_bytes,
        mime_type="image/png",
        file_size=len(sample_bytes),
    )
    async_session.add(img)
    await async_session.commit()
    await async_session.refresh(img)

    assert img.blob_content == sample_bytes
    assert img.image_index == 1


# ─── TB5：invite_code 表已删除（邀请码功能移除） ─────────────────────────────

@pytest.mark.asyncio
async def test_invite_code_table_removed(async_session):
    """invite_code 表已通过迁移删除，ORM 模型已不存在。"""
    import importlib
    import sys
    assert "app.core.models.invite_code" not in sys.modules, \
        "invite_code 模型不应再存在于已加载模块中"
    with pytest.raises((ImportError, ModuleNotFoundError)):
        importlib.import_module("app.core.models.invite_code")


# ─── TB6：prompt_template 枚举扩展 ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_prompt_template_game_observation_task_type(async_session):
    """PromptTemplate 可保存 task_type='game_observation'。"""
    from app.core.models.prompt_template import PromptTemplate

    pt = PromptTemplate(
        tenant_id=1,
        user_id=1,
        task_type="game_observation",
        version=1,
        content="你是幼儿游戏观察记录生成助手...",
        is_active=True,
    )
    async_session.add(pt)
    await async_session.commit()
    await async_session.refresh(pt)

    assert pt.task_type == "game_observation"
    assert pt.version == 1


@pytest.mark.asyncio
async def test_class_config_teacher_name_column(async_session):
    """ClassConfig 可保存 teacher_name 字段。"""
    from app.core.models.class_config import ClassConfig

    cfg = ClassConfig(
        tenant_id=1,
        user_id=1,
        grade="中班",
        class_name="阳光班",
        teacher_name="张老师",
    )
    async_session.add(cfg)
    await async_session.commit()
    await async_session.refresh(cfg)

    assert cfg.teacher_name == "张老师"


@pytest.mark.asyncio
async def test_prompt_template_homemade_teaching_task_type(async_session):
    """PromptTemplate 可保存 task_type='homemade_teaching'。"""
    from app.core.models.prompt_template import PromptTemplate

    pt = PromptTemplate(
        tenant_id=1,
        user_id=1,
        task_type="homemade_teaching",
        version=1,
        content="你是自制教玩具设计助手...",
        is_active=True,
    )
    async_session.add(pt)
    await async_session.commit()
    await async_session.refresh(pt)

    assert pt.task_type == "homemade_teaching"
