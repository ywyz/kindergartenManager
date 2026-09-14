# WP-B 独立只读 Review

2026-09-10；reviewer 角色，未递归委派，无文件写入权限。工作区 `/home/ywyz/code/km-wpb-20260910`。
最终复核开放 H/M/L = **0/0/0**；限本门功能与测试，不是CI、Office或产品发布验收。

| Finding | 证据/处理 | 最终 |
|---|---|---|
| 新confirmed reload投影必填参数破坏旧构造 | 旧W007用例TypeError RED；名称移至dataclass末尾，默认空字符串，实际重载传真实名称 | CLOSED |
| 默认split旧mock未匹配新六字段契约 | 5个旧client/service用例失败；默认mock显式名称，旧自定义五字段独立保留并测试 | CLOSED |
| 显式《名称》被清空、正文首行被误判名称 | 新8参数专项5 failed/3 passed；匹配两端书名号，拒绝正文/单行过程，只保留明确标题；8项GREEN | CLOSED |
| 每日Word通用填充strip丢名称前后空格 | 新保真专项1 failed；只对R6名称传preserve_whitespace=True；空白/换行与API一致 | CLOSED |
| 可编辑控件generation测试未列名称 | 将name_input加入既有控件守卫测试；原生产控件已绑定generation | CLOSED |

Main另补空白标题RED→GREEN；新快照期待更新为v2，独立v1写入/对账测试保持旧JSON/hash不变。
Unicode surrogate疑虑经Python继承关系和实测确认可由ValueError边界净化成AiParseError，撤回，不虚构修复。

Reviewer独立隔离执行 **209 passed in 9.21s**（当时测试集合），核对了名称、API、默认/自定义prompt、
W007、不可变证据、页面session守卫；日志位于 `/home/ywyz/code/km-wpb-evidence-20260910/reviewer-final-current.log`。
Reviewer确认Provider仍4 READ+2 DRAFT，名称不在Provider/Patch可写路径；源模板未改。
MySQL仅独立读取Main脚本/脱敏结果，未由reviewer再次运行容器；不得冒称双人重复数据库验证。

基线Bootstrap文案断言失败独立确认与WP-A未修改源码相同；不标通过。新文件Ruff通过；旧文件完整Ruff告警
另由Main逐文件对比基线，当前与基线均52条，新增诊断0。完整质量门不是GREEN。

## 最后范围修正

Main发现prompt_mgmt课程审议输出示例误加名称，基于实际course_review解析器输出键建立RED1 failed，
撤回该展示字段后受影响集合137 passed。最终本地提交`41b63c9cf6492d31c91faa07bd021e4096eb5379`，
前置全量与209项独立结果仍绑定此前实现内容，不伪称已在最终SHA再次全跑。最后窄复审另记如下。

Reviewer最后窄复核确认`41b63c9`只恢复课程审议原输出契约并新增对应守卫，split六字段仍限定本task。
独立隔离复跑页面守卫与课程审议客户端 **12 passed**；无新finding。最终开放H/M/L=0/0/0。
