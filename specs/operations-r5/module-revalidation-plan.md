# R2 五模块当前 SHA 复验计划

五个模块各自建立自动和人工证据；SQLite、真实 MySQL、真实 AI、浏览器和 Word 结果互不替代。

| 模块 | 自动门 | 隔离/人工门 | 当前状态 |
|---|---|---|---|
| 每日活动计划 | tenant/user/session、CRUD/history、revision/CAS/stale、单/批量 Word、Agent WRITE 与严格 4 READ + 2 DRAFT | SQLite、MySQL、真实文本 AI、当前浏览器、Windows Word 2010+ | `58 AUTO PASS / MANUAL BLOCKED` |
| 游戏观察 | 1/3 图、方向/压缩/BLOB、视觉 AI、CRUD/history/re-export、聚合失败全回滚 | SQLite、MySQL、真实视觉 AI、当前浏览器、Windows Word 2010+ | `40 AUTO PASS / MANUAL BLOCKED` |
| 一对一倾听 | 冻结规则 RED、五领域日期/工作日、15 图截断、串行生成、部分保存、CRUD、单条 2 种与批量 3 种导出 | P8/P8d、SQLite、MySQL、真实视觉 AI、当前浏览器、Windows Word 2010+ | `72 AUTO GREEN CANDIDATE / REVIEW M OPEN / MANUAL BLOCKED` |
| 自制教玩具 | tenant/user/session、文本 AI、编辑/保存/history/re-export/delete | SQLite、MySQL、真实文本 AI、当前浏览器、Windows Word 2010+ | `23 AUTO PASS / MANUAL BLOCKED` |
| 课程审议 | 拆课/AI/调整理由/修订稿、编辑/保存/history/re-export/delete；拒绝 R6 审批 scope creep | SQLite、MySQL、真实文本 AI、当前浏览器、Windows Word 2010+ | `29 AUTO PASS / MANUAL BLOCKED` |

一对一倾听冻结：图片稳定排序后最多 15；领域顺序固定为健康、语言、社会、科学、艺术；允许部分领域保存；
导出前默认全选当前可用领域且至少选一项；无数据/未选领域不生成空表/空文件。单条为合并 DOCX 或按领域 ZIP；
批量为合并 DOCX（幼儿间分页）、按幼儿 ZIP、按领域 ZIP。所有文档只含所选且有数据的领域/幼儿。

冻结 RED 提交 `5024fdc` 连续两次均为相同 `6 failed`：领域顺序、部分 combined 空表、批量合并、按幼儿 ZIP、
幼儿勾选顺序和页面三模式。GREEN 已补领域选择、模板顺序、单条两模式、批量三模式、同名幼儿 ZIP 防覆盖、
幼儿间硬分页与至少 15 图稳定截断。Review finding 另补连续两次相同 `2 failed`，锁定按领域 exporter 的逆序和
空选择回退；修复后倾听全组 `72 passed`。

当前仍有一个 Review M，故不得把一对一倾听标为完成：导出记录先提交、随后才复核 generation/session 并执行
独立 audit/download，存在窄窗口的证据不一致。这是既有多页面导出事务与独立审计边界问题；需另补稳定 RED 和
统一契约，不能在本次 Word 格式切片里用局部重排伪装原子性。历史列表 50 条上限不是冻结的“幼儿间分页”要求；
后者指批量合并 DOCX，已由 XML 硬分页测试覆盖。领域 UI 文案已改为“默认全选；仅导出当前可用领域”，导出层会
过滤未选/无数据领域，不生成空表或空文件；真实浏览器与 Windows Word 可见状态仍待人工验收。
