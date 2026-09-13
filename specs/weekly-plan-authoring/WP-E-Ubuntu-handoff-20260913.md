# WP-E Windows → Ubuntu 交接报告（2026-09-13）

本次将 Windows 补验报告、全部234个已封存证据文件（233项+清单自身）、独立复审、逐件矩阵及两份原隔离工作树未跟踪的WP-E范围提示词同步到本地交接分支。原产品实现和此前文档提交通过Git父历史完整保留，没有在main覆盖或拼贴产品文件。

## Git与验收基线

- 本地交接分支：`codex/wp-e-ubuntu-handoff-20260913`。文档交接提交SHA见迁移包`transfer-receipt.json`或恢复后的`git rev-parse HEAD`，不把它作为重新验过的产品SHA。
- 产品SHA：`0bded3377c01956833bcbb6cd306f9a7f5d924e1`；原文档后继：`247fc3472481bcdc7b161b36301e08f205da9c71`。
- 原main保留`8dcc83376577695b562529ec42adc6b48817f004`及其未跟踪WMP-9提示词；原Windows隔离分支和两份未跟踪WP-E提示词保留。交接提示词的仓库副本在`evidence/WP-E-source-prompts-20260913/`，仅为历史输入，执行范围以最新用户要求和本报告为准。
- 本轮只改变文档／验收证据，没有产品代码、模板、迁移或依赖变化；没有推送、合并main、远端CI、发布、生产操作或Issue消息。不假定远端已含这些本地提交。

## Windows结论与未关闭事项

| 范围 | 结果 |
|---|---|
| five-normal、five-holiday、six-sunday-normal、six-saturday-normal | 当前产品SHA／Microsoft365 Word2608客户端下候选格式PASS；逐件A4纵向1页、字体行距、内容、全部文字和边界、独立只读复审 |
| 原始4长文、用户采用4去重长文 | 保留历史原生各2页，单页FAIL；本轮没有新单页修订成功例 |
| 整体混合行距 | 可见文字分组选区实测固定20pt；末端空位置和合并结构限制保留，不写所有隐藏／空段统一20pt |
| 正式released/catalog资格 | NOT_VERIFIED；候选格式PASS不能直接安装成正式资格 |
| 应用无法收敛时拒绝下载、页面全分支、真实模型、数据库保存版本链 | 留待后续WP-E实际验收，本轮NOT_RUN |
| exact-SHA CI、OCI、迁移／部署及正式catalog安装 | 独立后续门；本次未执行、未授予生产操作权限 |
| WP-C四类历史native双RED | UNMET，用户允许继续WP-E本地工作决定保持 |
| WP-E／WP-F | WP-E总门OPEN；WP-F NOT_RUN，未生成WP-F-next-prompt.md |

Word账户与关于具体build分别保留在[environment.json](validation/wp-e-native-20260913/environment.json)。Windows Server2025已获接受，是DOCX兼容客户端，不是新增桌面产品。逐件范围见[完整原生报告](evidence/WP-E-native-Word-20260913.md)、[矩阵](validation/wp-e-native-20260913/windows-matrix.json)及[最终独立复审](validation/wp-e-native-20260913/review-delivery.md)。

## 文件组织与完整性

- 仓库`validation/wp-e-native-20260913/`：原封存234文件逐字节复制，保留Windows绝对路径为观察来源，不修改原JSON来伪装Ubuntu现场；`.gitattributes`禁用该目录换行转换。原`build_delivery.py`是Windows制证历史脚本，Ubuntu不要执行。便携验证使用下方新脚本。
- 迁移包`materials/`：四个目录`wp-e-header-week-20260912`、`wp-e-native-final-20260912`、`wp-e-reduction-20260912`、`wp-e-native-20260913`的全部现存文件，共380项。包含当前renderer原始DOCX、body、去重提案／采用记录／accepted-files、原生截图及历史候选。DOCX不提交Git，随外部材料包完整迁移；未保存或复制密钥、数据库、真实业务导出。
- [便携材料清单](evidence/WP-E-portable-materials-20260913.json)只定义这380个现存文件，不能替代历史清单。旧26项原脚本预期仍为`INTEGRITY_OK: 26 files; not Word or WP-E PASS`；历史native-final49/49，reduction38项中34匹配、4临时Word锁文件MISSING，保持原范围不修清单。
- 新233项清单已在Windows封存并复验。仓库和材料包副本需在Ubuntu再次按hash验证；Linux验证只能证明运输字节完整，不能代替新的原生Word验收。

## Ubuntu恢复与核对

将完整`wp-e-ubuntu-handoff-20260913.zip`复制到Ubuntu后解压。使用系统Python3标准库即可检查运输材料；无需先部署测试站或安装产品依赖。

```bash
unzip wp-e-ubuntu-handoff-20260913.zip -d wp-e-transfer
cd wp-e-transfer
python3 verify_transfer.py
git clone --branch codex/wp-e-ubuntu-handoff-20260913 kindergartenManager.bundle kindergartenManager
cd kindergartenManager
python3 specs/weekly-plan-authoring/verify_wp_e_handoff_20260913.py --materials ../materials
git status --short
git diff --name-only 0bded3377c01956833bcbb6cd306f9a7f5d924e1 HEAD -- app templates alembic requirements.txt
```

新clone应干净，最后一条产品路径diff应为空。bundle含该分支完整可达历史，不依赖Ubuntu已有远端或本地提交。需要沿用已有Ubuntu仓库时，先保护其未提交工作，再从bundle取入新分支；不要直接reset、覆盖或合并到main。

## 下一轮WP-E续作入口

1. 核对恢复SHA、AGENTS.md、ADR-0011、spec.md§2.2–2.7、tasks.md WP-E/F、WP-E-local-contract.md及本次矩阵；保留全部历史FAIL与UNMET。
2. 在用户指定的Ubuntu隔离开发／验收环境，先核实现有页面、配置和正式released/catalog实际状态，再确定可运行的页面分支。不要把候选通过或运输验证当作产品资格。
3. 按现有契约补实际页面生成／手改／采用或拒绝／保存重载／检查／导出及失效分支，真实模型、数据库链和目录资格分别记录实际输入、客户端与代码SHA；外部状态缺失的格子保持NOT_RUN/BLOCKED。
4. 只有已定位产品缺陷才做稳定业务双RED、最小修复、相关回归和独立复审。若改动影响Word输入或renderer，重新冻结产品SHA并重建受影响DOCX，旧Windows证据不自动继承。
5. 长文超页本身不是renderer缺陷；新改写须先展示事实与固定条数保持的具体差异并取得明确采用。已有去重采用不重复询问，不扩大为新提案授权。
6. WP-E所有必需门实际关闭前不执行WP-F；部署、生产、推送及Issue消息继续按独立授权处理。本报告只是交接，不执行这些后续动作。
