# R2 五模块当前 SHA 复验计划

五个模块各自建立自动和人工证据；SQLite、真实 MySQL、真实 AI、浏览器和 Word 结果互不替代。

| 模块 | 自动门 | 隔离/人工门 | 当前状态 |
|---|---|---|---|
| 每日活动计划 | tenant/user/session、CRUD/history、revision/CAS/stale、单/批量 Word、Agent WRITE 与严格 4 READ + 2 DRAFT | SQLite、MySQL、真实文本 AI、当前浏览器、Windows Word 2010+ | `58 AUTO PASS / MANUAL BLOCKED` |
| 游戏观察 | 1/3 图、方向/压缩/BLOB、视觉 AI、CRUD/history/re-export、聚合失败全回滚 | SQLite、MySQL、真实视觉 AI、当前浏览器、Windows Word 2010+ | `40 AUTO PASS / MANUAL BLOCKED` |
| 一对一倾听 | 冻结规则 RED、五领域日期/工作日、15 图截断、串行生成、部分保存、CRUD、单条 2 种与批量 3 种导出 | P8/P8d、SQLite、MySQL、真实视觉 AI、当前浏览器、Windows Word 2010+ | `62 LEGACY AUTO PASS / RED_AUDIT` |
| 自制教玩具 | tenant/user/session、文本 AI、编辑/保存/history/re-export/delete | SQLite、MySQL、真实文本 AI、当前浏览器、Windows Word 2010+ | `23 AUTO PASS / MANUAL BLOCKED` |
| 课程审议 | 拆课/AI/调整理由/修订稿、编辑/保存/history/re-export/delete；拒绝 R6 审批 scope creep | SQLite、MySQL、真实文本 AI、当前浏览器、Windows Word 2010+ | `29 AUTO PASS / MANUAL BLOCKED` |

一对一倾听冻结：图片稳定排序后最多 15；领域顺序固定为健康、语言、社会、科学、艺术；允许部分领域保存；
导出前默认全选当前可用领域且至少选一项；无数据/未选领域不生成空表/空文件。单条为合并 DOCX 或按领域 ZIP；
批量为合并 DOCX（幼儿间分页）、按幼儿 ZIP、按领域 ZIP。所有文档只含所选且有数据的领域/幼儿。

当前 source audit 已确认一对一倾听存在稳定 RED 候选：UI 领域顺序把艺术置于科学之前；单条导出没有领域
勾选；部分领域 combined DOCX 仍保留全部模板空表；批量 UI 仅有按领域 ZIP；选择使用 set/sort，不能保留
用户幼儿顺序。下一切片必须先把这些冻结为连续两次稳定 RED，再实施最小 GREEN。
