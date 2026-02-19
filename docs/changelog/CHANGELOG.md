# 📋 变更日志

所有版本更新记录。

---

## [0.1.1] - 2026-02-19

### 🐛 Bug Fixes
- **修复**: Word导出时室内区域游戏内容被填充到下午户外游戏的问题
  - 改进了 `normalize_label()` 函数，正确处理中间的冒号和换行符
  - 改进了 `fill_table_by_labels()` 和 `fill_by_row_labels()` 中的父字段检测逻辑
  - 现在能正确识别每个新的父字段上下文
  - 详见：[BUGFIX_EXPORT_ISSUE.md](../../BUGFIX_EXPORT_ISSUE.md)

### 📚 Documentation
- 创建完整的 `docs/` 目录结构
- 整合了所有项目文档，按以下分类组织：
  - `user-guide/` - 用户指南
  - `api/` - API文档
  - `architecture/` - 架构文档
  - `ai-integration/` - AI集成文档
  - `development/` - 开发指南
  - `changelog/` - 变更记录

---

## [0.1.0] - 2026-02-10

### ✨ Features

#### 核心库模块化
- ✅ `models.py` - 数据模型和常量定义（56行）
- ✅ `db.py` - SQLite数据库操作（115行）
- ✅ `word.py` - Word文档生成（170行）
- ✅ `validate.py` - 数据验证和工具（88行）
- ✅ `ai.py` - OpenAI API集成（82行）
- ✅ `__init__.py` - 统一接口（66行）

#### 功能完整性
- ✅ 教案数据验证
- ✅ Word文档自动生成
- ✅ SQLite/MySQL数据库支持
- ✅ AI智能拆分集体活动
- ✅ 学期信息管理
- ✅ 配置持久化（localStorage）

#### 文档系统
- ✅ README.md - 项目总览
- ✅ KG_MANAGER_README.md - 库文档
- ✅ QUICKSTART.md - 快速开始
- ✅ ARCHITECTURE.md - 架构设计
- ✅ CONFIG_UI_GUIDE.md - 配置指南
- ✅ REFACTOR_GUIDE.md - 重构说明
- ✅ examples_usage.py - 4个实际示例

### 🔄 Changed

#### 项目结构重构
- 旧结构：单一 `minimal_fill.py` 文件，逻辑混乱
- 新结构：模块化 `kg_manager/` 库，清晰的依赖关系
- 兼容性：保留 `minimal_fill.py` 作为向后兼容层

#### API改进
- `split_collective_activity()` 支持灵活的参数传递
- 支持自定义系统提示词
- 支持不同的AI提供商（OpenAI、兼容API、本地模型）

#### Word生成优化
- 改进了标签匹配算法
- 支持多行标签
- 改进缩进和格式处理

### 📦 Dependencies

```
nicegui>=1.3.0
python-docx>=0.8.11
openai>=0.27.0
chinesecalendar>=1.4.0
```

### 🐛 Known Issues

1. SQLite单线程限制 - 多用户场景应使用MySQL
2. AI输出格式偶尔不规范 - 需要改进提示词
3. Word字体在某些系统上显示不正确 - 需要系统支持仿宋字体

### 📚 Documentation Added

- README.md - 项目首页和功能总览
- KG_MANAGER_README.md - 300+行API文档
- QUICKSTART.md - 快速上手指南
- ARCHITECTURE.md - 400+行架构说明
- CONFIG_QUICK_REFERENCE.md - 配置快速参考
- CONFIG_UI_GUIDE.md - UI使用指南
- FILE_MANIFEST.md - 文件清单说明
- REFACTOR_GUIDE.md - 250+行重构说明
- REFACTOR_SUMMARY.md - 重构总结
- SESSION_SUMMARY.md - 会话记录
- COMPLETION_REPORT.md - 完成报告
- examples_usage.py - 4个可运行的示例

### 🎯 Testing

- ✅ examples_usage.py - 4个场景测试
- ✅ test_full_flow.py - 完整工作流测试
- ✅ test_fix_verification.py - Bug修复验证
- ✅ test_outdoor.py - 户外活动测试

### 🚀 Performance

| 操作 | 性能 |
|------|------|
| 验证教案 | <50ms |
| 保存教案 | <100ms |
| 生成Word | 500-1000ms |
| AI拆分 | 2-5秒 |

### 🔐 Security

- API Key存储在客户端localStorage
- 密码明文存储（建议：后续版本加密）
- MySQL连接支持认证

### 📞 Support

- 📖 文档：[docs/](../../docs/)
- 🐛 Issue：[GitHub Issues](https://github.com/ywyz/kindergartenManager/issues)
- 💬 讨论：[GitHub Discussions](https://github.com/ywyz/kindergartenManager/discussions)

---

## 未来计划

### 短期 (v0.2)

- [ ] 完整的单元测试覆盖
- [ ] HTTP API (FastAPI)
- [ ] 命令行工具 (CLI)
- [ ] 更多AI模型支持
- [ ] 数据迁移脚本

### 中期 (v0.3)

- [ ] MySQL专业支持
- [ ] 用户权限管理
- [ ] 教案模板库
- [ ] 批量操作优化
- [ ] 搜索和过滤功能

### 长期 (v1.0)

- [ ] PDF/Excel导出
- [ ] 云同步功能
- [ ] 移动应用（iOS/Android)
- [ ] 国际化支持
- [ ] 插件系统

---

## 许可证

MIT License

---

## 致谢

感谢所有贡献者的支持！

---

**最后更新**: 2026年2月19日
