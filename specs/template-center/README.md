# 模板中心第一期

本目录是模板基础设施的独立交付边界。下述“一期五类 enabled、周/月 reserved”是 WMP-7 前的冻结基线；
2026-09-06 的 WMP-7/T011-E 已在不改写该初始 registry 的前提下，用独立内部 registry 只启用 weekly/monthly，
且对业务仅开放 ACTIVE opaque binding、descriptor 只声明 READ capability。T007–T009 的 12 个 future RED 仍未实施。
权威内容见
[`spec.md`](spec.md)；T001–T011 的依赖、验收和最小 GREEN 顺序在 `spec.md` §6，测试门禁见
[`tests/README.md`](tests/README.md)。

一期只覆盖：

- global known 七类文档类型与 phase1 enabled 五类 registry（周/月两类 known-but-disabled）；
- 不可变版本、内容寻址安全存储、上传校验、激活/停用/回滚；
- version validation 与 active pointer 分离；每次授权 upload 新建版本，同 hash blob 去重；
- staged unit-of-work 提交，version/transition/audit 在 commit 前不可见；
- 受 Issue #55 policy port 控制的权限投影和最小脱敏审计；
- 合成预览、备份/隔离恢复、导出 resolve/render/parse 端口。

T011 另有一个仅供受控 seed/fixture 的周/月候选资格 job：它复用 T004 同一安全 validator，以及唯一
`TemplateExportPort` 的 opaque binding/render/parse；macro、外链、坏 ZIP、结构/profile mismatch 或不完整 Office
结果均 fail closed，不追加 passed evidence。T011-C 本身不提供 public projection、upload、preview、resolve_active、active、业务
读写或正式下载。证据和周/月独立 spec/RED/Review 全部通过后，才发布 registry 新版本启用这两个 known 类型。

一期不实现周/月业务模型、统一教学文档中心、审核流、GREEN 或迁移。`templates/weekplan.docx` 与
`templates/monthplan.docx` 是用户提供的候选模板，须等周/月独立 spec/RED 通过后才能接入；本目录的
测试不会读取、修改或跟踪它们。

建议命令：

```bash
.venv/bin/python -m pytest specs/template-center/tests --collect-only -q
.venv/bin/python -m pytest specs/template-center/tests -q
.venv/bin/python -m pytest specs/template-center/tests -q
```

稳定 RED 的失败属于预期结果；它不授权生产 GREEN、commit、push、CI、merge、Issue 关闭或 release。
