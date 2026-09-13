# WP-E Ubuntu 质量修复与应用验收（本地交付，WP-E仍OPEN/BLOCKED）

整体仍为 OPEN/BLOCKED；本文是本轮证据后继，旧账本保留原时点。产品及本地夹具已冻结 tested_code_sha `0b3656c919ddfe6f09db4ed0aa0732a828727a5c`；evidence_closure_sha 待验收文档完成后另记。

## 基线与保护

工作树 `/home/ywyz/code/km-wpe-quality-acceptance-20260913`，分支 `codex/wp-e-quality-acceptance-20260913`，从已核对交接HEAD101aedc08982521216e018692afb58ac0df1d91f创建。主仓库、干净交接树和旧Ubuntu续作树未作为写入位置，原始HEAD/status/staged/9文件hash保存在外部preservation-before.json。交接原包SHA25646db6410a3a159f161669f8889e1d1a1d390902d872e63c3ad8e6b85b66b1132。

GitHub API实时核对：交接远端101aedc，main8dcc83376577695b562529ec42adc6b48817f004；Quality34743993563 head101aedc失败。SSH只读访问失败后使用API，没有远端写入。标准库验证器前后结果均233/233、380/380、49/49、34/38且4旧锁文件仍MISSING、26/26。未重造缺项或执行旧Windows绝对路径制证脚本。

## 实现分工与质量原因

Codex负责范围、实际diff、独立复验、浏览器和文档；本地OpenCode1.18.30、opencode-go/glm-5.3-flash实现。Q1/Q2/Q3/Q3a/Q3b共用ses_f65366608ffeZZ0sYYX0qQgMdb；长会话在重复三个失败后终止exit130，传入当前状态新建Q3c会话ses_f6515a9a9ffeLVNHlp0eOQK3ZD；A1新隔离夹具会话ses_f6510da67ffeTc4e1ad35GO7Fd。没有Codex接手产品实现，没有模型/provider/付费方案切换。每轮独立任务书和精确读写/命令权限配置，无auto、分享、递归agent或远端写入。

调用修正均记录：数组型--file吞掉尾部提示词→把位置提示词置于flags前；证书错误→仅本进程NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt；权限相对路径匹配→同一批准文件加入相对路径；临时XDG目录导致原会话不存在→恢复默认OpenCode数据目录。没有关闭TLS或改全局代理。日志也保留被拒绝的未列入命令尝试；模型“无拒绝”文字不能覆盖真实事件。

原44项：16机械lint、13敏感异常诊断（12行）、15封存脚本诊断。Q1最小UTC/import/startswith/context组合；Q2十二行具体理由noqa，异常处理AST与原始相同；Q3先固定hash校验两manifest及全部270成员，仅精确排除六历史脚本的Ruff参数，不改原件或旧清单，不排除整个目录。新邻居、活跃验证器、策略脚本和测试仍lint；空参数仍校验并不裸跑Ruff。防漏检12项独立通过。完整44项表见交付附件ci-failures-resolution.md及原机器矩阵。

首次WRITE门另见两项陈旧测试假设：Agent offline DDL范围误包含后来WP-C在线反射迁移；Bootstrap测试仍期待自动迁移错误文案。Q3a只改两测试，保留四Agent触发器和无秘密/不隐式迁移断言；真实产品/migration未改。267项WRITE复验通过。

## 本轮真实业务缺陷

恢复隔离测试的已安装SimSun可见性后，实际PDF1页仍返回layout_geometry_invalid。冻结源码/hash及实际DOCX/PDF/SVG/bbox后，真实保存版本应用入口SQLite/MySQL各连续两次RED（共4次同因失败）。初次font_missing是环境前置失败，不能当业务RED；历史四类WP-C native双RED仍UNMET。

根因是Poppler把加粗宋体标题输出为复杂描边轮廓，原几何读取器要求所有描边均为直表格边。最小修复严格解析有限M/L/C/Z轮廓与6值matrix，使用变换后控制点保守bbox，只放行严格位于真实表格外的轮廓。表内/触边/畸形仍拒绝，缺边仍拒绝交付。fill_document/_text_complete AST不变、模板/字号/行距/固定数量/正文不变。独立reviewer无阻断问题，49项布局单文件通过；OpenCode51项包括另2项保存版本真实渲染，不混计范围。

## 资格与受影响候选

默认app.main startup不传word_port，空LayoutAuthority直接拒绝qualification_required。seed f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b，profile shared-weekly-v3.v1；本地released UUID00000000-0000-0000-0000-000000000801/version8/contract kg.template.weekly_activity_plan.candidate:2同hash。实际renderer LibreOffice26.2.5.2 620(Build:2)。正式五/六列材料、严格native-report、可信catalog装载/激活及独立审查尚缺，不把Windows矩阵改名伪造资格。

12份候选已独立再生成，全部输入及DOCX内部成员与原件相同：4正常LO1页fits，4原长文+4已采用去重LO2页layout_overflow。新目录word-revalidation-candidates含DOCX/PDF/逐页PNG/hash及新Word复验清单；PNG/PDF为LO辅助材料，原生Word NOT_RUN。历史0bded337候选格式PASS不继承为新代码PASS；历史八长文原生各2页FAIL不变。

## 当前验证与剩余工作

完整普通测试1762通过、1项因未启用无关R5_MYSQL_LIVE备份恢复演练而跳过；SQLite真实保存渲染2项均GREEN。真实页面已完成默认资格拒绝、五/六列下载、日历/来源、生成拒绝/采用/取消、手填/未保存提示、显式保存重载与双教师冲突；新长文候选采用待用户答复。依赖pip check通过；pip-audit2.10.1严格requirements审计无已知漏洞；Alembic唯一head d375e9ab2148且专属新SQLite已迁移。Foundation261通过；WRITE267通过；专属MySQL READ COMMITTED适用应用集104通过，renderer修复后实际渲染链2通过。数据库与mock/LO/浏览器/Word/云端证据分列，不用计数替代需求覆盖。

未执行push/PR/merge/Issue消息关闭/发布/OCI构建部署/生产迁移或资格安装/应用真实模型请求/WP-F。正式资格、新SHA原生Word、exact-SHA远端CI及云端门仍需独立条件与授权。本地质量通过不会声明新远端CI通过。

本地渲染环境前置：使用机器原有SimSun目录，通过仅本进程FONTCONFIG_FILE显式保留字体可见性；未复制/安装字体或改全局配置。实际LO及Poppler在本机可用。工作流当前未增加这些工具/字体的安装步骤，后续GitHub runner是否满足相同渲染前置尚未实测；不把本地全部GREEN当成新SHA远端Quality成功。

## 本轮用户补充约束

用户已检查 weekplan 模板内容无问题，明确五/六列排版由 Python 实现、不改变系统内置模板。本轮相对交接 HEAD 的 templates/ 差异为空；fill_document 从内置模板字节建立内存文档并计算五/六列宽度，源模板不写回。该内容确认单独记录，不冒充新导出文件的原生 Word 观察或正式资格。

## 浏览器与保存观察

真实Edge页面使用合成SQLite与mock AI。正常五列与前置周日六列均已检查并在下载目录收到DOCX（不是仅审计行/返回bytes）；五列文件SHA256 d7d3ee55e36757ae5e53ef298a44a50efa5a8b01a588e1d02b831113539d9ddf，六列见外部browser-downloads.json。周六六列与国庆节禁用列已实际读取。默认未资格实例明确拒绝，合成实例local_only=True，不构成正式资格安装。

来源页面实际显示零/一/双教师重复并明确选择，NULL名称保持手填。导入/三条缺项候选采用仅页面未保存，显式保存后另一教师读到结果和最后编辑者。随后双教师同版本保存一成一败，失败页保留输入，明确丢弃重载后看到成功主题。取消生成保持正文。单字段重生成第一次mock值与既有其他字段重复被拒，换成不重复的独立合成输入后只返回被选字段差异，拒绝保持。未flush手填检查提示先保存；已保存但缺项快照禁止导出。

只读DB校验：root1由revision2经两次明确保存到4，其他5根保持2；旧12版本、3日计划、18既有审计行hash保持。五/六列下载的两个根无新版本；ExportRecord始终0。来源快照只追加到新版本。人员未执行任何变更。详见[同目录需求矩阵](WP-E-Ubuntu-requirements-20260913.md)及外部browser-*-baseline/after.json、browser-observations.md。

合成长文实际2页超页后首轮mock产生26项差异：每个“围绕主题进行观察，”缩为“围绕主题观察，”，各10次与原末尾数字保持；33固定字段/各条数/7名称/主题/日期/人员保持。已按用户原始请求发起明确采用问题，尚无答复，未采用/未保存该正文；历史8长文与模板不变。采用后的本条浏览器保存重检保持PENDING_USER_DECISION，不能用自动化通过填成浏览器PASS。

## 实现会话后续与独立复审

A1原会话ses_f6510da67ffeTc4e1ad35GO7Fd长期无事件后终止，无helper落盘；拆分seed会话ses_f6506a13affeetZexnamprAKzC在中断边界落盘第一版，已保存源/hash且续接修正，不覆盖重做。A2 serve会话ses_f64fcbc1fffeAclHTaRaaNFfPz及同会话三项反馈完成；helper最终hash049835b13f07b6a8cf84ef8c7c66f13387659307cd7d067bb5648dc6dd2b7ae2。最终事件索引包含17个实际事件文件及任务书/权限配置hash，原始错误/拒绝/中断保持。

Codex已独立复验；exception_review分别完成质量/异常、几何renderer、helper只读复审，均无阻断问题。helper残余仅限不接受不受控目录：receipt非DB摘要绑定/未排除hard link，本轮两新fixture单独核验；没有扩大为通用生产工具。seed已有目录/dangling symlink拒绝验证通过，serve仅回环、真实app.main、不再seed/migrate，不读取真实AI配置或调用网络。

## 剩余门与最小后续

- 新合成长文：等待本轮具体候选明确采用/拒绝；采用时只执行现有候选采用、显式保存、真实重检，仍超页则保留正文拒绝文件。TTL仍生效，不绕过、不自动重试。
- 正式资格：按qualification-gap-map.md补绑定五/六列真实原生观察、可信catalog审查/装载/激活；用户模板内容确认未要求改变此独立证据角色。
- 新代码Word复验：12份受影响候选及tested-code-binding.json已准备；4正常历史PASS不能继承，8长文历史2页FAIL保留。Ubuntu本轮未做原生Word。
- 新SHA远端Quality/云端/应用真实AI：NOT_RUN；无push/发布/部署/真实模型授权。当前CI未提供本机字体/LO环境证据，后续runner前置需实测。
- WP-C四类历史native双RED继续UNMET。WP-E整体OPEN/BLOCKED，不进入WP-F。

外部证据根：`/home/ywyz/code/wp-e-coordination-20260913`。原件前后校验、全部真实命令/日志、任务书/反馈/模型会话、44项处理表、资格缺项、独立复审与再生成候选均在此；不包含生产数据。主仓库/交接树/旧续作树HEAD/status/staged及9初始hash前后相同，原包SHA256不变。
