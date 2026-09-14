# WP-E 云端测试准备（未部署）

状态：准备核对完成，当前交付尚无可验收的新云端镜像；新环境MySQL、登录、共享编辑与实际导出 NOT_RUN。生产部署单独执行。用户指定非生产目标后，按以下顺序执行，不把旧站存活或本地SQLite结果当作本轮云端通过。

## 当前缺口

- Dockerfile仅安装gcc，没有LibreOffice Writer、Poppler及fontconfig；默认Compose没有四项资格环境变量或只读catalog挂载。
- 子代理只读核对BWH现有kg-wmp9-staging：旧源码revision c08c8fb，旧Alembic版本3c9f4b2a7d1e，容器没有LO/Poppler/fontconfig、资格配置和当前shared_weekly代码。旧staging的health/readiness/login可达仅为旧站状态。
- BWH宿主宋体可见不等于容器可见；本轮目标镜像仍需实际fc-match和字体hash核对。不得从任意来源下载或提交字体。
- 当前代码Alembic head为d375e9ab2148；须在独立空MySQL显式迁移，不能以启动create_all或health代替。
- 已审阅本地catalog要求LibreOffice版本严格等于26.2.5.2 620(Build:2)。目标镜像若不同，必须在目标环境重新生成/审阅资格材料，不能仅改版本字段。
- 现有BWH Caddy已占用80/443，不能直接启动根Compose的另一个Caddy争抢端口。

## 可执行顺序

1. 选择独立非生产项目、域名/loopback端口、数据库和数据卷，保留旧staging。使用独立测试镜像定义和Compose覆盖配置；镜像包含libreoffice-writer、poppler-utils、fontconfig和已授权宋体供应。
2. 新镜像绑定源码SHA及immutable repository@sha256 digest；在该镜像容器内实际运行 `libreoffice --version`，检查 `pdftotext`、`pdfinfo`、`pdftocairo`、`fc-match`，并核对 `fc-match -f '%{family} %{file}' SimSun` 与字体SHA。源码Dockerfile或宿主输出不能替代这些证据。
3. 只读挂载完整受信catalog；提供 `KM_WEEKLY_LAYOUT_MANIFEST`（容器绝对路径）、独立审阅得到的 `KM_WEEKLY_LAYOUT_SHA256`、目标租户 `KM_WEEKLY_LAYOUT_TENANT_ID`、`KM_WEEKLY_LAYOUT_ACTIVATE=1`。普通启动必须验证released binding、模板hash和实际渲染器版本，配置缺失/漂移拒绝导出。不得使用local-synthetic资格。
4. 独立空MySQL迁移至d375e9ab2148，核对数据库readiness；初始化合成教师及同班授权，经HTTPS实际登录，双教师共享编辑/冲突保护，五列六列保存下载，长文超页拒绝→手动缩短→保存重检→浏览器收件。每项单独记录。
5. 记录新镜像digest/源码SHA/迁移版本/浏览器收件及失败项，随后才讨论生产部署。不得复用生产凭证、数据库或把临时测试配置安装为生产配置。

本轮未创建或改变云端测试环境。历史CI的宋体供应缺口仍保留，不关闭或绕过CI检查。
