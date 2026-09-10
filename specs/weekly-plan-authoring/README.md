# 周计划阶段资料与Windows交接

本目录于2026-09-10汇总到`handoff/wp-a-windows-20260910`分支，供Windows拉取。
该分支继承WP-B `41b63c9cf6492d31c91faa07bd021e4096eb5379`及WP-C身份子步
`00afdc878b306475508c777997956cdf4638dbef`，汇入最新WP-A/B/C未提交设计和交付资料。
历史账本中“尚未提交/无可访问链接”描述当时状态，保留原文，不据本次同步改写历史证据或CI结论。

**当前Windows任务入口：[WP-A-Windows-validation-prompt.md](WP-A-Windows-validation-prompt.md)。**

- [可携带的九份合成样本及Linux参照](validation/wp-a-simsun-20260909/README.md)
- [WP-A宋体/Office历史边界](evidence/WP-A-fonts-20260909.md)
- [WP-B交付](evidence/WP-B-20260910.md)
- [WP-C身份子步及尚缺接口](evidence/WP-C-20260910.md)
- [Windows之后的WP-C下一小步](WP-C-next-prompt.md)

同步仅提交既有代码/最新项目文档和必要合成QA材料；不包含字体二进制、密钥、数据库、业务导出、
运行缓存或机器配置。原工作区及WP-A/B/C工作树全部保留，main未合并，不创建PR或发布部署。
源模板/产品代码在本次交接未更改；新增的校验脚本仅计算样本文件完整性。
外部Linux运行目录的历史日志/运维脚本仍是历史本地路径，Windows任务使用本目录自带材料，
不依赖重新执行那些Linux命令。没有因为上传历史材料产生新的Office/云端/Quality PASS。
