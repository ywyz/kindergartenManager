# WP-E Windows 续作 2026-09-12

WP-E BLOCKED / NOT COMPLETE；WP-F 未执行，未生成 WP-F-next-prompt.md。

本轮外部材料目录：`C:/Users/admin/.codex/visualizations/2026/09/12/01a0937c-3f64-7ce2-98f9-fecd1934901c/wp-e-windows-evidence-20260912`。交付包为同级 `WP-E-Windows-20260912.zip`，含新旧候选/输入/hash清单、保全源码和复审记录，不含安装环境或运行配置。使用 `verify_windows_preparation.py` 核对；此校验不是Word或WP-E PASS。

**最新状态：**下文初始核查段落记录修复前状态。随后独立复审确认假日集体活动格错误，已取得双业务RED并完成最小修复/独立源审，冻结新产品SHA `908f4a2cd076b5bc08d2373db34a966d7ace7919`，分支 `codex/wp-e-windows-holiday-20260912`。当前正式待验输入为 `candidates-fixed` / `candidate-manifest-fixed.json`；原8件只作修复前保全。新SHA的全部适用验证仍须逐项记录，不继承9cde的历史回归为本轮通过。

远端 fetch 后 origin/feat/wp-e-continuation-20260912 为 84f189f160808c0001cd9d316d6b99fbf6816f34，与用户已知HEAD无差异。隔离 worktree 为同级 wp-e-windows-84f189f，detached HEAD。产品基线 9cde71655c30cafdc6ac4e99ed22509ad989b121 → 文档后继 7c0acb9337534d0db60b9ff6d9e1abd09e382643 → 84f189f；app/tests/alembic/templates/requirements 零产品差异。

首先执行原 verify_bundle.py，得到 INTEGRITY_OK: 26 files; not Word or WP-E PASS。后续再验相同。没有改写清单。26份只覆盖便携副本，不包括本轮DOCX或完整Linux外部829/318材料；那些外部材料本轮未现场获得，不能声称全量重验。

Windows 初次 Git 检出 core.autocrlf=true，33项代码清单有32项字节不一致。crlf-before.json 保留原hash；原blob与规范化LF匹配。普通 checkout-index 未全部刷新，默认git archive亦受autocrlf影响；最终使用 git -c core.autocrlf=false archive 保留 frozen-head-lf.zip 并仅恢复隔离worktree，再核验33/33原始hash匹配。该worktree索引重新核对与HEAD无差异。无产品实现修复，无业务RED声明；main 未切换，原未跟踪 WMP-9-windows-acceptance-prompt.md 保留，没有将它用于当前验收。

AST解析迁移链唯一head为 d375e9ab2148；未运行数据库迁移。使用打包Python 3.12.14仅作标准库核验/DTO生成，不冒充项目Python3.14.7全栈测试。隔离辅助依赖仅新增chinesecalendar1.11.0，当前代码对日历数据和标签hash校验通过。没有启动业务应用、连接业务库或真实模型。

用户确认目前使用仓库这份模板，Ubuntu目标站点以后测试。模板hash f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b；源码声明released UUID 00000000-0000-0000-0000-000000000801 / version8 / kg.template.weekly_activity_plan.candidate v2。当前Ubuntu实际运行代码/镜像/绑定仍待核验，不将源码声明或用户模板确认升级为云端released证据。

本轮8份DOCX均由当前 fill_document 生成，profile shared-weekly-v3.v1；数据为新合成教师内容，日期来自固定日历包，未伪装真实来源/页面保存版本。candidate-manifest.json逐件绑定body、display、DOCX、生成器、种子和检查状态。正常/长中文、三教师、空格、《》、数量、跨月/假期、前置周日/周六和换行均有输入；全部原生项NOT_RUN。长文未经缩减或人工改写，不预写单页。

本机为用户接受的Windows Server2025 Datacenter，具体OS与Word注册表线索见environment.json；原生账户/关于Word尚缺。会话工具无原生Word可见控制，需用户提供WORD-OBSERVATION.md要求的全部页观察。辅助render_docx.py实测缺soffice.exe，日志render-probe.log保留；不改用COM/OOXML/PDF估计替代原生资格，也不以缺LO阻塞Windows原生验收。

## 未完成目标页面矩阵

以下为本轮现场状态；历史本地浏览器仅保留原记录的范围。Ubuntu目标尚未提供受控页面与相应执行范围，不能执行或外推云端覆盖。

| 分支 | 本轮状态 | 后续必须观察 |
|---|---|---|
| 来源零/一/多（含本人+他人） | NOT_RUN | 无源待填、单源选择、重复全列出，未选不导入 |
| 缺项生成/选字段重生成 | NOT_RUN | 仅授权必要输入、已有手填不覆盖、差异拒绝/采用 |
| 双教师人员共享 | NOT_RUN | 默认修改、新建初始化、另一教师打开不覆盖已存人员 |
| 来源检查/重导入 | NOT_RUN | 修改/删除/不可见提示、三值差异、取消与手改历史不变 |
| 取消/过期/漂移 | NOT_RUN | session/assignment/source/mapping/prompt/page/template/version等待前后重验 |
| 保存/只读对账 | NOT_RUN | 无变化不新增版本、commit_unknown不重试/不重发下载 |
| 并发/撤销 | NOT_RUN | 双创建同根、双CAS一胜一败、撤销两种线性化、等待中输入保护 |
| 实际超页→有限缩减 | NOT_RUN | 保存后真实检测、拒绝不变、最多两次、显式采用保存重检、仍超页手改 |
| 导出收件/持久化 | NOT_RUN | 保存版本、下载实际收件、无新增ExportRecord/长期候选、审计无正文、临时清理 |

## 独立外部门

原生Word矩阵和独立逐页复审：NOT_RUN。正式catalog输入/安装/恢复：BLOCKED，未创建或激活任何catalog。默认空catalog失败关闭不等于正式导出PASS。

exact-SHA CI只读结果、OCI不可变digest、目标Ubuntu运行SHA/数据库revision、受控云端页面、真实模型配置与授权、凭据/迁移/部署均分别待核验。当前没有自动操作生产、发布或发Issue消息。用户推迟Ubuntu验收不是这些门已满足。

WP-C四类历史native双RED仍UNMET：source audit composite FK、imported/adopted hash nonempty、source/mapping event identity、reimport revision lower bound。用户允许继续WP-E本地工作的决定保留。177/178原始hash与重写时序解释、历史long三份两页FAIL、compact仅合成候选都不改写。

若后续确认新行为缺陷，先保全修复前源/hash并连续两次稳定业务RED，再最小修复、相关回归、独立只读复审，重新冻结产品SHA和适用证据。当前准备辅助脚本的环境/检出失败不是产品RED。

下一步先收取账户/关于Word和8件全部页原生材料；独立复审通过后再核验可信catalog输入及Ubuntu目标当前released事实与安装授权。只有WP-E实际完整关闭，才能依据tasks.md WP-F全矩阵写下一步提示词。

## 本轮新缺陷与修复

独立reviewer确认 shared_weekly_word.py 将假期label填入集体活动格，违反spec§2.3。已有测试错误地期望同样标签。本轮六份含假期候选实际证实；holiday_activity_red.py先核对原body hash，再调用真实当前fill_document并断言假日集体活动空白，两次连续exit1，失败日期/内容一致。源归档frozen-head-lf.zip、原8件、脚本和RED日志/hash receipt保留，不修改原交付清单。

最小修复只把非教学日集体活动改空字符串，更正五/六列既有断言并加连续假期首日断言。相同探针GREEN空失败列表；独立只读复审见independent-preparation-review.md。没有修改日期事实、晨谈节日标签、字号、行距或模板。新生成8件保留相同输入body，单独输出新DOCX hash；没有把旧文件改名冒充新证据。

本地冻结提交因未配置Git作者首次失败；随后仅此commit命令使用Codex <codex@localhost>，未更改用户全局/仓库身份配置。代码SHA为908f4a2cd076b5bc08d2373db34a966d7ace7919。未推送，不存在从此本地提交推导exact-SHA远端CI或OCI的依据。

额外安装Python3.14.7到外部隔离目录成功；自动注册运行时因Windows注册表权限失败，不影响直接调用，该环境错误不计业务RED。uv frozen同步长时间无进展后停止，改requirements安装并保留dependency-install.log；实际测试运行与依赖版本必须按最终日志解释，不能声称frozen锁安装完成。

## 最终本轮验证范围

完整requirements安装也在网络缓慢、仍解析下载依赖阶段停止，未启动任何业务服务。为完成当前纯DOCX边界的必要检查，在外部准备依赖目录安装pytest/pytest-asyncio，使用Bundled Python3.12.14执行真实仓库测试：

`python -m pytest --noconftest tests/test_wpe_word_layout.py -q -k 'controlled_seed or incomplete_draft or formal_qualification or consecutive_holiday or emitted_table'`

结果 `6 passed, 8 deselected in 0.94s`，日志pytest-layout.log。--noconftest仅排除数据库公共fixture装载；所选测试不使用该fixture。检查范围为五六列固定格式/回读、缺项拒绝、空资格拒绝、连续假日留空、原模板边框。8个实际renderer测试因缺依赖未运行，不算跳过通过。该运行不是Python3.14.7全栈回归，未冒称170项/全仓/Foundation/两库通过。

新SHA适用的SQLite每连接FK/专属MySQL迁移与并发撤销、取消/replay/unknown、旧版本/来源/人员保全、常规/Foundation/旧周月/Agent、lint/format及真实renderer完整复验仍需在依赖齐全的隔离环境补齐。diff检查已通过。原生Word矩阵、target Ubuntu云端矩阵与正式资格仍NOT_RUN/BLOCKED。用户允许继续本地准备，不消除这些剩余门。

主工作树最终仍为main 8dcc83376577695b562529ec42adc6b48817f004，唯一未跟踪文件原WMP-9-windows-acceptance-prompt.md保留，当前hash7555bb301d6a569f8c6e4a041f478be6688d713b66244466f26f73018b2ad4ee。没有对主工作区文件执行写操作。所有运行数据、安装和输出都位于独立授权目录；不能把运行目录加入交付包。
