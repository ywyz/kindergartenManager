# WP-E Ubuntu交接独立只读复审（2026-09-13）

结论：当前本地交接内容和便携验证通过复审，未发现阻断项。此结论是文档／证据运输准备，不是Ubuntu产品验收或WP-E关闭；Git提交、bundle和最终zip尚待主操作agent制作并恢复核验。

## 范围与证据

- 当前交接工作树分支codex/wp-e-ubuntu-handoff-20260913，复审时HEAD为247fc3472481bcdc7b161b36301e08f205da9c71。实时git diff显示六个现有状态文档仅21行新增指针；相对产品0bded3377c01956833bcbb6cd306f9a7f5d924e1的app、templates、alembic、requirements.txt无差异。
- 阅读新交接报告、原生报告仓库导航副本、verify_wp_e_handoff_20260913.py、portable-materials清单和换行属性。原生报告副本新增导航，原封存字节另存且不改。
- 独立逐字节比较源今日目录与validation/wp-e-native-20260913：234对234文件，名称集合及全部字节一致，其中233清单成员和清单自身。没有修改封存目录。validation/.gitattributes对该树禁用文本换行转换。
- 两份原隔离工作树未跟踪WP-E提示词副本逐字节相同；其局部.gitattributes禁用换行转换。副本明确作历史输入，不覆盖最新授权。第一次比对脚本误把新增.gitattributes当成源提示词，报FileNotFoundError；按*.md范围重新比对通过。这是审查脚本范围错误，不是业务RED或材料缺失。
- 正常4件只记当前SHA/Word客户端下候选格式PASS，原始4长文及已采用4去重长文仍两页FAIL；可见段落20pt与整体混合、空段／合并结构限制保留。正式released/catalog、应用拒绝下载和其他页面分支、真实模型、数据库保存链、CI/OCI/迁移部署仍在后续门。WP-C四类历史双RED仍UNMET、WP-E OPEN、WP-F NOT_RUN，不生成WP-F-next-prompt。

## 实际执行的便携检查

在此交接工作树，用当前标准库Python执行：

`python specs/weekly-plan-authoring/verify_wp_e_handoff_20260913.py --materials ../transfer/materials`

退出0，原始输出为：

```text
INTEGRITY_OK: 26 files; not Word or WP-E PASS
NEW_EVIDENCE_INTEGRITY_OK: 233 files
PORTABLE_MATERIALS_OK: 380 existing files
wp-e-native-final-20260912: 49/49 MATCH; 0 historical MISSING retained
wp-e-reduction-20260912: 34/38 MATCH; 4 historical MISSING retained
HANDOFF_INTEGRITY_OK; candidate-only Word result retained; formal qualification and WP-E remain OPEN
```

脚本使用传入materials路径及仓库相对路径，未依赖原Windows绝对目录来寻找材料；保留历史清单38项和四个特定MISSING，检查所有现存材料大小/hash及集合，另运行原26文件验证。380便携现存文件范围没有被偷换成历史38/38完整。此Windows执行不伪称已在Ubuntu运行；恢复后仍应执行相同脚本。

## 后续运输核验边界

交接报告的恢复步骤明确完整bundle clone指定分支，保护已有Ubuntu未提交内容，避免reset或覆盖main。原始DOCX放外部materials、不提交Git；证据目录的Windows绝对路径保留原始观察来源，不伪造Ubuntu现场。已封存历史build_delivery.py明确不在Ubuntu执行。

最终bundle/zip尚未在本报告生成时制作，因此本审查不报告其SHA、大小或恢复成功。建议制作后按报告执行verify_transfer、bundle独立clone及便携脚本，确认新clone干净、产品路径diff为空；这些是运输验证，不增加产品测试或生产授权。未请求push、远端、生产、Issue消息或WP-F动作。本复审只新增此文件。
