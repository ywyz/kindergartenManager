---
applyTo: "app/repository/**,alembic/**,app/core/models*"
---

# 数据库与 ORM 约定

## 必须遵守的字段约定

所有业务表（非纯配置表）必须包含以下字段，字段名和类型不得更改：

```python
from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

class BaseModel(Base):
    __abstract__ = True
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
```

## 迁移规则

1. **禁止**在应用启动时调用 `Base.metadata.create_all()`
2. 所有 schema 变更必须生成 Alembic 迁移脚本：
   ```bash
   alembic revision --autogenerate -m "描述变更内容"
   alembic upgrade head
   ```
3. 生成后必须人工检查迁移文件，autogenerate 不能识别所有约束

## Session 管理

- 使用 `AsyncSession`（NiceGUI 底层 async）
- 每个请求/操作使用独立 session，通过依赖注入传入 repository 层
- 禁止在 service 层或 ui 层直接操作 session

## 查询约定

- 所有查询必须携带 `tenant_id` 过滤条件，避免跨租户数据泄露
- 分页查询使用 `limit` + `offset`，禁止全量加载后 Python 切片
- 敏感字段（如 `api_key_encrypted`）查询后禁止在日志中打印原始值
