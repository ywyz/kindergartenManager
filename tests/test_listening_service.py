"""P5 — 一对一倾听服务层测试。

覆盖：未配置视觉 Key、正常生成、指标缺失补默认 3 星、DB 提示词覆盖、整记录持久化。
"""
import unittest.mock as mock
from datetime import date

import pytest

from app.core.exceptions import ConfigError
from app.integration.image_processing import CompressedImage
from app.integration.image_storage.blob_backend import BlobImageStorage
from app.service.listening_service import generate_domain_content, save_record_with_all

_FAKE_IMAGE = b"\xff\xd8\xff\xe0" + b"\x00" * 100


async def _seed_catalog(session, n=2):
    """插入 n 个 健康/小班/下学期 指标，返回其 id 列表（按 sort_order）。"""
    from app.core.models.indicator_catalog import IndicatorCatalog
    from app.repository.indicator_repository import list_indicators

    for i in range(n):
        session.add(IndicatorCatalog(
            tenant_id=1, grade="小班", term="下学期", domain="健康",
            level1_name="身心状况", level2_name=f"指标{i}", sort_order=i,
            standard_star1="a", standard_star2="b", standard_star3="c",
        ))
    await session.commit()
    cats = await list_indicators(session, 1, "小班", "下学期", "健康")
    return [c.id for c in cats]


def _ai_return(n_images=1, indicators=None):
    return {
        "goals": "目标1；目标2",
        "image_descriptions": [f"图{i+1}" for i in range(n_images)],
        "indicators": indicators if indicators is not None else [
            {"sort_order": 0, "stars": 2}, {"sort_order": 1, "stars": 1},
        ],
        "evaluation": "综合评价" * 10,
        "support_strategy": "支持策略" * 10,
    }


_CTX = {"grade": "小班", "term": "下学期", "child_name": "小明", "child_age": "4岁"}


async def test_no_vision_key_raises(async_session):
    """未配置视觉 Key → ConfigError。"""
    with pytest.raises(ConfigError):
        await generate_domain_content(
            session=async_session, tenant_id=1, user_id=1,
            domain="健康", images=[_FAKE_IMAGE], context=_CTX,
        )


async def test_generate_domain_ok(async_session):
    """正常生成：返回五段内容 + 指标结果 + 压缩图片，触发审计。"""
    from app.repository.ai_key_repository import save_ai_key

    cat_ids = await _seed_catalog(async_session, 2)
    await save_ai_key(async_session, tenant_id=1, user_id=1,
                      api_base_url="https://api.example.com/v1",
                      plain_api_key="sk-v", model_name="gpt-4o", key_type="vision")

    with (
        mock.patch("app.service.listening_service.generate_listening_domain",
                   return_value=_ai_return(1)) as mock_ai,
        mock.patch("app.service.listening_service.compress_image",
                   return_value=mock.MagicMock(data=b"c", mime_type="image/jpeg",
                                               width=10, height=10, file_size=1)),
        mock.patch("app.service.listening_service.log_audit") as mock_audit,
    ):
        result = await generate_domain_content(
            session=async_session, tenant_id=1, user_id=1,
            domain="健康", images=[_FAKE_IMAGE], context=_CTX,
        )

    assert result["goals"] == "目标1；目标2"
    assert result["image_descriptions"] == ["图1"]
    assert len(result["compressed_images"]) == 1
    # 指标结果覆盖 2 个目录指标，catalog_id 正确
    assert [r["catalog_id"] for r in result["indicator_results"]] == cat_ids
    assert [r["stars"] for r in result["indicator_results"]] == [2, 1]
    mock_ai.assert_awaited_once()
    mock_audit.assert_called_once()
    assert mock_audit.call_args[0][0] == "ai_listening"


async def test_default_three_stars(async_session):
    """AI 未覆盖的指标默认 3 星。"""
    from app.repository.ai_key_repository import save_ai_key

    await _seed_catalog(async_session, 2)
    await save_ai_key(async_session, tenant_id=1, user_id=1,
                      api_base_url="https://api.example.com/v1",
                      plain_api_key="sk-v", model_name="gpt-4o", key_type="vision")

    partial = _ai_return(1, indicators=[{"sort_order": 0, "stars": 1}])  # 只给 sort 0
    with (
        mock.patch("app.service.listening_service.generate_listening_domain", return_value=partial),
        mock.patch("app.service.listening_service.compress_image",
                   return_value=mock.MagicMock(data=b"c", mime_type="image/jpeg",
                                               width=10, height=10, file_size=1)),
        mock.patch("app.service.listening_service.log_audit"),
    ):
        result = await generate_domain_content(
            session=async_session, tenant_id=1, user_id=1,
            domain="健康", images=[_FAKE_IMAGE], context=_CTX,
        )

    stars = {r["sort_order"]: r["stars"] for r in result["indicator_results"]}
    assert stars == {0: 1, 1: 3}  # sort 1 未给 → 默认 3


async def test_prompt_from_db_overrides_default(async_session):
    """DB 有激活 one_on_one_listening 提示词 → 作为 system_prompt 传给 AI。"""
    from app.repository.ai_key_repository import save_ai_key
    from app.repository.prompt_repository import save_new_version

    await _seed_catalog(async_session, 1)
    await save_ai_key(async_session, tenant_id=1, user_id=1,
                      api_base_url="https://api.example.com/v1",
                      plain_api_key="sk-v", model_name="gpt-4o", key_type="vision")
    await save_new_version(async_session, tenant_id=1, user_id=1,
                           task_type="one_on_one_listening", content="我的提示词")

    with (
        mock.patch("app.service.listening_service.generate_listening_domain",
                   return_value=_ai_return(1, indicators=[{"sort_order": 0, "stars": 2}])) as mock_ai,
        mock.patch("app.service.listening_service.compress_image",
                   return_value=mock.MagicMock(data=b"c", mime_type="image/jpeg",
                                               width=10, height=10, file_size=1)),
        mock.patch("app.service.listening_service.log_audit"),
    ):
        await generate_domain_content(
            session=async_session, tenant_id=1, user_id=1,
            domain="健康", images=[_FAKE_IMAGE], context=_CTX,
        )

    assert mock_ai.call_args.kwargs["system_prompt"] == "我的提示词"


async def test_save_record_with_all(async_session):
    """save_record_with_all：写主表 + 各领域 + 图片 + 指标结果，计数正确。"""
    from app.repository.listening_image_repository import list_images_by_record
    from app.repository.listening_repository import (
        get_record_by_id, list_domains_by_record, list_indicator_results,
    )

    ci = CompressedImage(data=b"\xff\xd8\xffimg", mime_type="image/jpeg", width=10, height=10)
    domains = []
    for d in ["健康", "语言"]:
        domains.append({
            "domain": d, "obs_year": 2026, "obs_month": 4,
            "date_1": date(2026, 4, 1), "date_2": date(2026, 4, 6), "date_3": date(2026, 4, 13),
            "goals": f"{d}目标", "evaluation": "评价", "support_strategy": "策略",
            "compressed_images": [ci, ci, ci],
            "image_descriptions": ["d1", "d2", "d3"],
            "indicator_results": [{"catalog_id": 1, "stars": 2}, {"catalog_id": 2, "stars": 3}],
        })

    record_data = {
        "tenant_id": 1, "user_id": 1, "obs_year": 2026, "obs_month": 4,
        "child_name": "小明", "adult_count": 1, "child_age": "4岁",
        "grade": "小班", "term": "下学期", "class_name": "向日葵班", "observer": "王老师",
    }

    rid = await save_record_with_all(
        async_session, record_data=record_data, domains=domains, storage=BlobImageStorage(),
    )

    assert (await get_record_by_id(async_session, 1, rid)).child_name == "小明"
    assert len(await list_domains_by_record(async_session, 1, rid)) == 2
    assert len(await list_images_by_record(async_session, 1, rid)) == 6  # 2 领域 × 3 图
    assert len(await list_indicator_results(async_session, 1, rid)) == 4  # 2 领域 × 2 指标
    health_imgs = await list_images_by_record(async_session, 1, rid, domain="健康")
    assert health_imgs[0].image_description == "d1"
    assert health_imgs[0].blob_content == b"\xff\xd8\xffimg"
