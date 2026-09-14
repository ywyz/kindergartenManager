# ADR-0010：云端在线系统是唯一产品交付形态

- 状态：接受
- 日期：2026-09-07
- 关联：ADR-0001、ADR-0003、ADR-0007、WMP-9、Issue #55/#56/#57

> 产品负责人已明确确认目标变更：KindergartenManager 面向部署在云服务器上的在线系统，
> 不再把 Windows、Linux 或其它桌面/本地安装包作为独立产品形态。

## 背景

仓库历史上同时保留源码、本地 SQLite、Windows/Linux 打包和 Docker 部署说明，容易把开发运行方式、
历史构建产物、Office 文档兼容性环境与产品交付形态混为一谈。当前生产能力和运维门禁已经围绕
Caddy、主应用、MySQL、不可变 OCI 镜像、HTTPS、readiness、备份和回滚建立，因此需要冻结单一目标。

## 决策

1. 唯一产品交付形态是部署在云服务器上的在线 Web 系统，用户通过受支持浏览器和 HTTPS 访问。
2. 生产参考拓扑保持模块化单体：`Internet → Caddy → NiceGUI app → MySQL 8`。发布和回滚只使用与
   source SHA、Release 元数据收敛的不可变 OCI 镜像引用。
3. Windows installer/portable、Linux portable、Debian 桌面式安装包和自动打开本机浏览器不再属于产品
   路线、发布门或用户验收矩阵。已有脚本、workflow 和历史产物只是遗留兼容资产，不代表受支持交付；
   是否删除它们须另行建立清理任务并验证不影响云端发布。
4. 源码启动和 SQLite 继续用于开发、自动测试、隔离验收和故障诊断，不构成面向用户的本地应用。
   生产参考数据库为 MySQL 8；SQLite 兼容性仍由迁移和回归测试守卫。
5. Microsoft Word 和 LibreOffice 只作为云端系统导出 DOCX 的外部消费端兼容性环境。它们验证原始
   exporter 字节的打开、显示、打印和 PDF 转换，不运行 KindergartenManager，也不形成 Windows/Linux
   两套应用。
6. WMP-9 正式业务验收应在隔离、受控、与生产拓扑等价的云端在线环境执行 UI/application 权限和导出
   路径；Windows Word 与 Linux LibreOffice 证据作为独立文档兼容性结果记录。未经发布/部署门授权，
   不得把验收环境推广到生产。

## 当前实现差距

2026-09-08 的独立部署准备变更已将 `.github/workflows/release.yml` 收敛为 Docker 双平台构建、
仅上传镜像 descriptor 和 draft Release 验证，移除桌面构建、上传与面向用户的安装说明。
历史打包代码仍保留；工作流本地验证不代表远端镜像、发布或生产部署已经完成。

## 后果

- README、用户手册、路线图、系统架构、人工测试矩阵和后续提示词统一使用“云端在线系统”定位。
- 本地开发命令保留在开发者文档，并明确只用于开发/测试。
- 不再要求或宣传 Windows/Linux 本地安装、升级、卸载、数据目录或 Defender 验收。
- 云端交付仍必须分别证明镜像完整性、HTTPS、数据库 readiness、登录、权限、关键业务、备份恢复和回滚；
  单个平台容器测试或 Office 文档打开结果不能替代这些门。
- 本 ADR 不授权发布、生产部署、删除遗留打包代码或修改 WMP-9 业务/权限契约。
