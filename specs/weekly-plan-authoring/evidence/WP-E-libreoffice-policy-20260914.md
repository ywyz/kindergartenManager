# WP-E 本轮 LibreOffice 验证口径与继续执行记录

用户于 2026-09-14 授权：“授权跳过windows验证过程，直接进行下一步，到时候正式部署时windows有问题，我会跟你沟通，目前使用libreoffice系列验证”。

本轮 Windows 原生 Word 验证状态调整为 `SKIPPED_BY_USER`，不再作为 Ubuntu 下一步工作的前置阻塞；该状态不表示 Word PASS。当前文档兼容性以 LibreOffice 实测为依据。此前提示词、交接文件中要求先返回 Windows 材料才能继续的流程，在本轮由本授权覆盖；历史报告、封存清单和失败事实保留。

## 已进入下一步：Ubuntu 材料审查

- 当前交付基线：`c69b9e4435c0a70c4801836cb3d901728216af0e`；tested_code_sha：`2c310b7f170c8cc509e0c9ddcb8d8c0a2322c427`。当前交付工作树开始时干净；主仓库三份既存修改未动。
- 本次执行 `python3 scripts/wpe_windows_handoff.py verify --package /home/ywyz/code/wp-e-startup-coordination-20260913/word-revalidation-candidates --frozen-sha 2c310b7f170c8cc509e0c9ddcb8d8c0a2322c427 --manifest-sha256 175ae794759a220f890e2a9e8fa30ff36590ef2166706dbc6ac8697574704c42`，退出码 0，56 份文件完整性通过。脚本原始输出仍为 `WP_E_WINDOWS_HANDOFF_INTEGRITY_OK: 56 files; Word and qualification remain NOT_RUN`；它是运输校验，不是新客户端观察。
- 复用未变候选的已有 LO 记录：LibreOffice 26.2.5.2 620(Build:2)，4 正常候选各 1 页，8 长文候选各 2 页，长文 `layout_overflow`。本次没有重新渲染，不将记录写成新的视觉验收。

## 剩余执行范围

1. 继续 WP-E Ubuntu 收尾，以 LO 检查五/六列、正常/长文、日期假期、字体行距、全部页文字及裁切；未改变的有效证据可以复用。
2. 正式资格适配仍待实现：当前 `LayoutAuthority` 的非 local catalog 要求 `role=word-native` 与 `client.product` 以 `Microsoft Word` 开头。不得用 LO 报告冒充 Word，亦不得将 `local-synthetic` 安装为正式资格；需要显式 LO 资格语义和针对性验证，保留模板/released binding/hash/失败关闭约束。
3. 长文超页不能因跳过 Windows 而视为通过。`focus.0–2` 已确认，其余23字段仍须展示差异并取得内容决定；本次授权不等于整份缩减采用。随后才可执行适用的采用、保存、重检及下载链路。
4. 当前 WP-E 仍 OPEN；正式资格适配/安装、长文链路和适用外部门未完成，不预写阶段三或 WP-F PASS。部署仍是后续任务，Windows 问题按用户届时反馈处理，本记录不额外要求部署前补做 Windows 验证。

本次仅新增流程决策与材料核验记录，没有修改产品、模板、候选、数据库或封存文件；没有提交、推送、部署或回写 Issue。
