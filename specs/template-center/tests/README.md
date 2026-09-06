# 模板中心稳定 RED 说明

本目录只穿过模板中心未来的公开 `app.service.template_center` seam，测试不导入尚不存在的生产模块到
collection 阶段；各测试在用例内部延迟导入，以保持 collection clean。测试使用确定性的内存 blob/version/
transaction/audit/policy/export/backup ports 和合成 OOXML bytes，不读取真实模板、数据库、真实凭据或网络，不使用
`sleep`、`skip`、`xfail`、源码文本匹配或生产私有字段。

## 文件与矩阵

| 文件 | 行为矩阵 |
|---|---|
| `test_template_center_registry_red.py` | global known 七类、phase1 enabled 五类、周/月 disabled 拒绝、不可变版本摘要、权限投影和 tenant scope |
| `test_template_center_upload_red.py` | `.docx`/ZIP/XML/宏/外链/路径/压缩炸弹/占位符校验、hash/size、重复 hash 新版本、staged 失败原子性 |
| `test_template_center_lifecycle_red.py` | validation 与 active pointer 分离、validated 重复 active、CAS/stale/跨租户拒绝、active 唯一、blob 不删除、审计 |
| `test_template_center_preview_export_red.py` | synthetic-only preview、零持久化、resolve/render/parse 版本证据、无 active 不 fallback |
| `test_template_center_backup_red.py` | manifest 闭合、owner-only/隔离 staging、篡改/未知成员/权限/路径/tenant/hash 失败和原子恢复 |
| `test_template_center_candidate_qualification_red.py` | T011 受控周/月 seed/fixture qualification、前置拒绝与安全阶段 macro/external-rel/bad-ZIP/structure-profile mismatch、Office failed/缺 LibreOffice/缺 evidence ID/精确版本/关闭的 `microsoft-word/ooxml-docx` 兼容目标、同一 opaque export port render/parse、无 public CRUD/active/正式 Preview |

测试对应的最小公开对象和方法在 [`../spec.md`](../spec.md) §3.3、§3.7、§3.10、§3.11 中冻结；T011 内部候选资格
窄 seam 在 §3.12 冻结。候选资格测试不把内部 job 当作 `TemplateCenter` 公共 API。端口的 fake 只记录可观察调用和
效果；测试不得通过 `_private` 属性推断实现。

## RED 门禁

```bash
.venv/bin/python -m pytest specs/template-center/tests --collect-only -q
.venv/bin/python -m pytest specs/template-center/tests -q --tb=no
.venv/bin/python -m pytest specs/template-center/tests -q --tb=no
```

必须满足：

1. collection 成功且无 collection error；
2. 连续两次 collected/passed/failed 和失败 node ID 完全相同；
3. 失败只指向缺失/未满足的 `app.service.template_center` 正式 seam；
4. 无 skip/xfail、固定长 sleep、真实网络/凭据、模板工作树写入或生产迁移；
5. 这些测试不替代 Issue #55 权限矩阵、模板契约 ADR、周/月独立 spec/RED、T011 candidate qualification evidence 或当前五类 Word 人工验收。

完成 RED 后先做双轴 Review；只有 Review 0/0、明确 GREEN 授权且 T001/T002 已接受，才按 spec §6 的
T003–T011 顺序实现。当前目录的 RED 结果不构成 GREEN、合并、发布或 Issue 关闭证据。

## 2026-09-02 本地 RED 证据

在正式生产模块尚未创建的当前工作树执行：

```text
.venv/bin/python -m pytest specs/template-center/tests --collect-only -q
49 tests collected

.venv/bin/python -m pytest specs/template-center/tests -q --tb=no
49 failed in 0.11s

.venv/bin/python -m pytest specs/template-center/tests -q --tb=no
49 failed in 0.11s
```

两次失败 node ID 完全一致；`--tb=short -x` 的首个异常为
`ModuleNotFoundError: No module named 'app.service.template_center'`。无 skip、xfail 或 collection error。
这是缺失正式 seam 的预期 RED，不是生产实现或 GREEN 授权。

## 2026-09-06 T006 / T011-C 串行门证据

T006 在 `cfa141a3fdbd094560d057e47a50bd733cbc5256` 完成 tenant/document-type scoped active pointer、
CAS activate、deactivate 与 rollback；exact-SHA Quality/CodeQL 均通过，Issue #56 保持 OPEN。

T011-C 的自动实现候选 `tested_code_sha=301c2d5f2b247cb5544783f2494de97366810480`：

- 独立初始 RED 连续两次 `5 failed / 39 passed`；reviewer 的 rendered-bytes 绑定 finding 再先固定为
  连续两次 `4 failed / 41 passed`，之后才由 main 修复；
- 专项 `45 passed`；T003–T006 + T011-C 累积 `216 passed`；全库 `1129 passed / 1 skipped`；
- 模板中心全目录 `231 passed / 12 failed`，12 项均为未实施的 T007–T009 既定 future RED；
- 独立只读 reviewer 最终 Code H/M/L `0/0/0`，Standards/Spec/scope-creep `0/0/0`；
- 两个 released candidate 均由唯一 validator 验证，LibreOffice `26.2.5.2` 实际打开并导出；服务器
  不运行 Word，资格 evidence 使用关闭的 `microsoft-word/ooxml-docx` 兼容目标并绑定实际 rendered SHA；
- 未实现 WMP-6 orchestration、active/CRUD/业务读写或正式下载；两份用户模板保持未跟踪、未提交。

最终 evidence closure SHA、exact-SHA Quality/CodeQL 与 Issue 回写以 Issue #56 为外部证据；该门不关闭 Issue。

## 2026-09-06 WMP-6 前置治理说明

上述 T011-C 是已经完成的模板中心单候选 qualification，不能再以 `WMP-6 / T011-C` 别名重新宣称。它的
evidence 只绑定当时未跟踪的原始 weekplan/monthplan hash。后续 WMP-6 是独立的周/月应用层 orchestration：只会严格
串行调用本目录已经完成的 `TemplateCandidateQualificationJob.qualify` seam，不复制 validator、registry、contracts 或
export port。

用户随后明确授权清除两份模板中的机构、班级、人员、日期、示例正文、文档作者/时间、应用 GUID、custom XML/properties
和修订标识，并将脱敏文件提交。
当前新 hash 为：

- `templates/weekplan.docx`：`f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b`
- `templates/monthplan.docx`：`f2e5dbe2a468dd15c55cdd6b70c5e15fe63048a3708b151732e208703b0d11f4`

本次字节变化不会倒推修改、覆盖或作废历史记录本身，但旧 qualification evidence 不能证明新文件已 qualified。WMP-6
GREEN 前必须由另一个明确授权的模板中心证据门决定新 seed/profile 版本并对这两个精确 hash 重新 qualification；在此之前
保持 reserved/disabled，不执行 T011-E，不创建 active pointer、TemplateVersion、ExportRecord 或正式下载。

## 2026-09-06 当前脱敏候选 qualification evidence refresh

本门从已完整验证并推送的 `f752eb6713954e6081965c02e62394505304ce6f` 开始，仅追加当前脱敏候选的
关闭 profile/evidence，不覆盖上节历史 T011-C：

- 历史 weekly/monthly v1 handle、profile、version、contract version 与旧 hash 原样保留；
- 新增 `controlled-weekplan-seed-v2` + `weekly_activity_plan-profile-v2`，profile/contract/structural version
  均为 2，精确绑定 `f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b`；
- 新增 `controlled-monthplan-seed-v2` + `monthly_theme_activity_plan-profile-v2`，profile/contract/structural
  version 均为 2，精确绑定 `f2e5dbe2a468dd15c55cdd6b70c5e15fe63048a3708b151732e208703b0d11f4`；
- `weekly-monthly-fixture-v1` 与既有 renderer/parser v1 保持不变；v1/v2 handle/profile 交叉组合均在 seed
  读取前失败关闭。

稳定 RED 先于生产实现提交：最终为 9 collected、5 passed / 4 failed，连续两次节点及失败集合一致；node-only
SHA-256 为 `0d9c5f5bdfce901452d0b220807c2af53d7a463787f97db39eccc9dbec9738bd`，failure-node SHA-256
为 `7c34a268453d3b5dfcc858d73b740de5df78d4f302222243368c91140502a254`。最小 GREEN 只向关闭 registry
追加两项 profile，并让既有 profile 构造器显式承载版本；`TemplateCandidateQualificationJob.qualify`、唯一 validator、
contracts、export/parse 与 Office 完整性判断均未复制或改写。refresh 9 项与既有 T011-C 45 项合计 54 passed。

真实 Office 证据使用 LibreOffice `26.2.5.2 620(Build:2)` 分别打开并导出两个精确输入。输入在执行前后 hash
不变；导出 DOCX 再次通过唯一 validator：

| evidence reference | 输入/rendered SHA-256 | 导出 DOCX SHA-256 / structure SHA-256 | PDF SHA-256 / 页数 |
|---|---|---|---|
| `candidate-refresh-20260906-weekly-v2-lo-26.2.5.2` | `f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b` | `2fc90678f7a30d711331e6e17fa6c491d3da0ea25bd5bdb8ecf2de8a6e13750e` / `dab4a78999831c486f9df25400f82800d2f4ff18ce076571cc9c64a830efe9c6` | `4c701dc189459f94707970c763ae24627089f3109e8bcdb5042a8f3a8c69d215` / 2 |
| `candidate-refresh-20260906-monthly-v2-lo-26.2.5.2` | `f2e5dbe2a468dd15c55cdd6b70c5e15fe63048a3708b151732e208703b0d11f4` | `27042d45f6193468d4292911ddae1fe0586e0188ee4a1b33df0abc1ea2070f9e` / `2c97f5602d9afbd45b240871a5f5b1ea789cccabcc566378c776f1c2b63829a4` | `751044a51d81ebb6ecb07e2c09dbbe376897f7636682744907b9f50c7e40a19b` / 1 |

临时 DOCX/PDF 已清除；证据只保留关闭摘要，不保留正文或路径。独立只读 reviewer 对代码、Standards、Spec、
scope-creep 的 H/M/L 均为 0/0/0。周/月两类型仍为 reserved/disabled；本门没有 WMP-6 GREEN、T011-E、active
pointer、TemplateVersion、ExportRecord、正式下载或业务写入。最终 exact-SHA Quality/CodeQL 和 evidence closure
以 Issue #56 的追加评论为准，Issue 保持 OPEN。
