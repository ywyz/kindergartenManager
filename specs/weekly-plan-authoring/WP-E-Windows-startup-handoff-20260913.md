# WP-E Windows 启动交接（2026-09-13）

本文件定义 WP-E 阶段一 Ubuntu 产物到阶段二 Windows Word 原生观察的可恢复交接。
阶段二和阶段三尚未执行；本文和随附模板不能作为任一阶段的 PASS。WP-F 不在本交接范围内。

## 输入、绑定和生成边界

交接使用仓库中的 `scripts/wpe_windows_handoff.py`。它只接受：

- 一个绝对路径、HEAD 与 `--frozen-sha` 完全相同且无改动/未跟踪文件的 Git 工作树；
- 旧 `word-revalidation-candidates/manifest.json`；
- 旧清单对应的绝对 `--source-root`，其中每个 case 目录含 `body.json` 和清单声明的
  `candidate.docx`、`candidate.pdf`、PNG 等文件；
- `libreoffice`、Poppler (`pdfinfo`、`pdftotext`、`pdftocairo`、`pdftoppm`)、`fc-match`，
  且 `fc-match SimSun` 必须实际解析到 `SimSun`。不接受用其他字体冒充 SimSun，也不复制受限字体。

旧清单中的历史绝对 `source_body` 只作为记录，不被读取。helper 按 case id 从
`source-root/<case-id>/body.json` 读取，并逐件核对清单声明的源文件 hash；case 目录中历史
`lo-profile` 等未声明文件可以存在，但不会进入新包。源清单不被改写。

只有在产品 SHA 已冻结后才执行：

```bash
cd /home/ywyz/code/km-wpe-startup-handoff-20260913
.venv/bin/python scripts/wpe_windows_handoff.py prepare \
  --repo /abs/frozen/worktree \
  --source-manifest /abs/word-revalidation-candidates/manifest.json \
  --source-root /abs/word-revalidation-candidates \
  --output /abs/new-wp-e-windows-handoff \
  --frozen-sha <40-lowercase-hex-sha>
```

`prepare` 会从 `--repo` 导入 `fill_document`、authoring contracts、layout contracts，记录
这些实际源码文件的相对路径和 SHA，并校验受控 `templates/weekplan.docx` 的
`f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b`。它不会安装资格、写数据库、
修改模板或启动应用真实 AI。

它还从同一冻结仓库的 immutable released port 调用 tenant 11、WEEKLY_ACTIVITY_PLAN 的
resolve_active，把 template_version_id、released version、content_sha256、contract_id
和 contract_version 写入包 manifest。该值只是当前 released 依赖的可复核快照；它不表示
Windows 已观察 Word，也不执行生产资格安装。若 released binding 与受控模板 hash 不一致，生成
立即失败关闭。

便携验证必须同时从独立交接说明取得可信的冻结产品 SHA 和交接清单 SHA。Ubuntu/Windows
可以本地重新计算清单 hash 作比对，但不能把刚从包内读取后自行计算的值当作信任输入：

```bash
.venv/bin/python scripts/wpe_windows_handoff.py verify \
  --package /abs/new-wp-e-windows-handoff \
  --frozen-sha <same-40-lowercase-hex-sha> \
  --manifest-sha256 <sha256-of-handoff-manifest.json>
```

验证器在解析 JSON 前先校验清单 hash，然后拒绝绝对路径、路径穿越、symlink、额外文件、缺失
文件、大小差异和内容 hash 差异。包内的每个文件都在逐件 manifest 中列出。`prepare` 失败时不
复用半成品目录；完整包名称和 hash 由实际冻结 SHA 生成后再填写交接报告。

Main 组装最终交付包时还应放入可恢复源码 bundle/补丁、独立文档、逐轮 OpenCode 失败记录、
实现/RED-GREEN 和只读复审 JSON 等材料，并生成包根的 delivery-manifest.json：

```json
{
  "schema": "wp-e-startup-delivery.v1",
  "tested_code_sha": "<40-lowercase-hex>",
  "evidence_closure_sha": "<40-lowercase-hex>",
  "files": [
    {"path": "source.bundle", "bytes": 123, "sha256": "<64-lowercase-hex>", "role": "recoverable-source"},
    {"path": "evidence/review.json", "bytes": 123, "sha256": "<64-lowercase-hex>", "role": "independent-review"}
  ]
}
```

helper 的 verify-delivery 只按该清单逐件核验安全相对路径、大小和 hash，且要求从独立交接
说明取得清单 hash 和冻结 SHA：

```bash
.venv/bin/python scripts/wpe_windows_handoff.py verify-delivery \
  --package /abs/final-delivery \
  --frozen-sha <trusted-tested-code-sha> \
  --manifest-sha256 <trusted-delivery-manifest-sha256>
```

它不生成 bundle、不猜测 evidence closure，也不把包内自述变成可信来源。缺少清单、源码恢复
材料或独立复审材料时，最终交接不得宣称完整。

## 包内文件角色

每个 case 目录包含以下阶段一文件，文件名和角色有意区分：

| 文件 | 角色 | 阶段二可否当作 Word 证据 |
|---|---|---|
| `input.body.json` | 从旧清单源目录保留的正文输入 | 可作为正文 hash 输入，不能证明渲染 |
| `runtime-candidate.docx` | Ubuntu 受控源码重新生成的待观察 DOCX | 是 Windows 打开的输入，打开前须逐件核 hash |
| `runtime-lo.pdf` | Ubuntu LibreOffice runtime 辅助 PDF | 否，不能替代 Word 导出 PDF |
| `runtime-lo-page-N.png` | Ubuntu LibreOffice runtime 辅助页面图 | 否，不能替代 Word 页面图 |

`runtime-lo.*` 只记录 Ubuntu renderer、Poppler 和字体诊断，并在 case 中记录
`inspect_local` 的 `fits/pages/reason`。这项本地观察是 unqualified 辅助结果；它不能激活
`LayoutAuthority`。阶段二必须另行生成并命名：

- `word-export.pdf`：Windows Microsoft Word 导出的 PDF；
- `word-page-N.png`：从该 Word 导出 PDF 或 Word 原生页面取得的 Windows 观察图；
- `native-report.json`：Windows 实际观察报告。

`word-export.*` 与 `runtime-lo.*` 不互相替代，不能改名覆盖，也不能用 Ubuntu PDF/PNG 的 hash
填入 Word 字段。阶段二不修改产品、模板、schema 或候选正文；发现输入 hash、renderer、released
binding 不匹配时停止并报告差异。

当前 v1 资格 schema 只把 renderer 的 LibreOffice product/version 作为绑定字段；Poppler 版本和
字体解析文件及其 hash 属于运行环境旁证，不会自动因二进制 hash 漂移而使资格失效。现有运行时仍实际检查
SimSun family 与页面几何；若未来要把 Poppler/字体二进制 hash 纳入失效条件，必须另定契约，
不能由 Windows 改写当前 schema。

## Windows 阶段二填写规则

Windows 从仓库拉取冻结分支/commit，先验证仓库 SHA、模板 SHA、包 manifest SHA 和每个 case 的
`input.body.json`、`runtime-candidate.docx`。不接受孤立 SHA；需要仓库分支或 bundle/可应用补丁
以及本文件、helper、测试、模板和逐件 manifest。

对 12 个 case 逐项保留原正文和人员、日期、主题、五/六列及条数。打开同一份
`runtime-candidate.docx`，记录 Word 的产品和完整版本/build；不临场改正文、字号、行距、模板或
schema。每个 case 产生 `word-export.pdf`、逐页 `word-page-N.png` 和一份待审
`native-report.json`。报告必须写实际观察；没有观察的字段保持 `NOT_RUN`，不能预填 PASS。

当前资格校验器接收的 native observation 是以下 17 个且只能是这些字段：

```text
schema, role, client, renderer, columns, body_sha256, template_sha256,
profile, pages, page_observations, font, font_pt, line_pt, fixed_counts,
docx_sha256, pdf_sha256, png_sha256
```

使用仓库的 `evidence/WP-E-Windows-return-template-20260913.json` 另存到新的 Windows 返回目录；不要把返回文件放入已封存的阶段一包，否则整包校验会报告额外文件。模板内观察字段保持 `NOT_RUN`，不能将规格中的期望值复制成实际观察。

**`client` 和 `renderer` 的语义不同。** `client` 记录实际 Microsoft Word 产品和完整版本；native report 的 `renderer` 必须逐字绑定阶段一清单所记的 **LibreOffice 运行时 product/version**，它表示待资格化的应用运行时，不表示 Word PDF 的生成软件。现有 `SharedWeeklyWordPort.verify_runtime` 只接受 `renderer.product=LibreOffice`，若把此字段写成 Word，普通启动将拒绝。Word PDF 的生成客户端由 `client` 和独立 Word 环境记录说明；不得把 LO PDF 放入 Word artifact 项。

只有实际观察成立时，阶段三审查才允许填入当前校验器要求的单页观察值：`pages=1`、唯一逐页结论 `all_text_visible_no_clipping_no_overflow`、正文 `font=SimSun/font_pt=12/line_pt=20`、固定数量 `[2,1,3,1,3,3,3,3,3,1]`。标题保持受控模板自身要求，不能为单页缩小标题或正文。A4、正文完整、裁切、日期/人员/主题等必须有实际 Word 页面证据支持。多页或失败如实记录，不转换为合格值；八份长文不为凑资格而删改。

当前外层 `weekly-layout-qualification.v1` 恰好接收以下结构：

| 层 | 精确字段及关系 |
|---|---|
| 外层 | `schema, profile, template_sha256, renderer, client, role, fixtures, released_binding` |
| `fixtures` | 恰好两项，列数集合恰好为5和6；每项仅 `columns, body_sha256, artifacts, observation` |
| `artifacts` | 仅 `docx, pdf, page-1.png, native-report.json`；每项仅 `file, sha256` |
| artifact 路径 | `file` 必须是同一catalog目录内的普通文件basename，不能含子目录路径或symlink |
| `observation` | 对应原生报告文件的SHA256，等于 `artifacts.native-report.json.sha256` |
| `released_binding` | `template_version_id, version, content_sha256, contract_id, contract_version`，与实际immutable released port逐字一致 |

阶段二返回全部12份候选观察。阶段三仅在材料真实且审阅通过后，从已观察的一页正常候选中选择一个五列、一个六列fixture；其余候选报告独立保留，不能把12份全部塞进只允许两项的资格清单。组装时可将两套文件以 `5-`、`6-` 前缀复制到新的catalog目录以满足basename约束，保持原字节与hash，不覆盖阶段二原件。`artifacts.pdf/page-1.png` 绑定对应 Word 导出PDF/页面图，runtime LO文件仅旁证。没有合格五/六列材料时不生成可激活资格。

清单中的 `released_binding_tenant_id=11` 只是本地合成环境的immutable port观察，**不是生产激活证明或生产租户默认值**。实际目标租户只能由运维独立设置 `KM_WEEKLY_LAYOUT_TENANT_ID`；当前schema不从候选教学字段、姓名或manifest自行授予租户资格。

阶段二只产生事实、文件 hash 和报告；它不安装正式资格。阶段三若要形成正式资格材料，必须由
运营者另行把已复核的五列/六列 Word fixture、`native-report.json` 和当前正式 released binding
按 `weekly-layout-qualification.v1` 组装，manifest 的 `renderer/client/role/template_sha256`
与每个 artifact hash 必须逐字匹配当前 `LayoutAuthority._read`。`local-synthetic` 只能进入明确
`local_only=True` 测试 authority，不能转成生产 `word-native` 资格。当前模板中的
`formal_qualification`、`windows_word_observation` 和 return template 都保持 `NOT_RUN`。

## 交接安全边界

交接包不得包含密钥、数据库、真实教学/儿童数据或用户凭据。不得推送、合并、部署、生产迁移、
生产资格安装、Issue 消息或关闭 Issue。Windows 只负责真实 Word 观察和证据回传；不得通过修改
产品/schema/模板来凑材料，也不得执行 WP-F。
