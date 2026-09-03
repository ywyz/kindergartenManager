# 模板中心第一期任务门

本表是 [`spec.md`](spec.md) §6 的可执行索引。所有状态初始为“待前置门/稳定 RED”；完成文档与 RED
不等于允许实现 GREEN。

| ID | 任务 | 前置 | 通过证据 | 最小 GREEN 边界 |
|---|---|---|---|---|
| T001 | 接受角色/跨教师/审核/导出/删除矩阵 | Issue #55 冻结 | policy version、反向授权矩阵、审计规则 | 不改模板代码 |
| T002 | 接受 Word 模板权威/版本/安全/回滚 ADR | ADR-0008（并确认 ADR-0004/0007）；T001 | ADR 状态“接受”、链接与本 spec 一致 | 不改模板代码 |
| T003 | 冻结 global known 七类、phase1 enabled 五类、DTO、错误码和端口 | T001/T002 | stable RED Review 0/0 | 只建 contracts/registry |
| T004 | 纯上传校验 | T003 | 合成 OOXML 安全/占位符/结构矩阵 | 只实现无副作用 validator |
| T005 | 内容寻址 blob 与不可变 validated 版本 | T004 | hash/size/重复 hash 新版本/blob 去重/失败原子性 | 只实现存储与版本元数据 |
| T006 | validated version 与 active pointer 分离、CAS、停用、回滚与 audit | T005 | 并发 stale、validated 可重复 active、唯一 active、审计完整性 | 不接 UI/exporter |
| T007 | policy projection 接线 | T001、T006 | 当前 session、tenant/user、角色变化、disabled 类型和越权负向 | 不扩展 Issue #55 能力 |
| T008 | synthetic preview 与 export parser port | T006/T007 | synthetic-only、零持久化、版本 hash 追踪、无 fallback | 不改业务字段 |
| T009 | backup/isolated restore | R5-R、T006 | owner-only artifact、manifest、篡改/路径/tenant/hash 原子失败 | 不运行生产恢复 |
| T010 | 五类 exporter 分开接线 | T008/T009 | 每类独立 RED/GREEN、Word/LibreOffice 人工验收 | 一次只接一类 |
| T011 | 周/月 reserved candidate qualification 与 enablement gate | T010；两个独立周/月 spec/RED/Review | 受控 seed/fixture；同一安全 validator 拒绝 macro/external-rel/bad-ZIP/structure-profile mismatch；Office status、Word/LibreOffice 精确版本和 evidence ID 完整；全部通过后发布 registry v+1 启用七类 | 内部窄 job；无 public projection/upload/preview/resolve_active、active、业务读写或正式下载 |

## 状态纪律

- T001/T002 未接受前，RED 只能讨论候选契约，不得实现模板管理。
- T003–T009 每个任务都要有自己的稳定 RED；Review finding 必须先追加 RED 再修正。
- T010 的五类 exporter 不能在同一个变更中合并周/月业务。
- T011 的 candidate qualification 不是正式 Preview：只能消费受控 seed/fixture、复用 T004 安全 validator，并在
  synthetic render/parse 后检查 Office status、Word/LibreOffice 精确版本和 evidence ID；任何前置、安全或 Office
  失败都不能追加 passed evidence、创建 version/active/ExportRecord 或业务读写。只有周/月模型、字段映射、Word
  解析和人工验收标准及该 evidence 全部通过后，才可发布新 registry/contract 版本启用两个 reserved 类型。
- 任一局部 GREEN 不代表 Standards/Spec 0/0、固定 SHA、merge、Issue 关闭或 release。
