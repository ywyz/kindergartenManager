# WP-E Ubuntu 资格启动与 Windows 交接阶段一

状态：执行中。阶段二 Windows 原生复验和阶段三返回材料资格审查尚未执行；不预写 PASS。WP-E 仍 OPEN/BLOCKED，WP-F 未执行。

## 基线与保护

本轮从实时核验的文档后继 `877831c5fb968a4945cdec78789422c89a68ec02` 创建工作树 `/home/ywyz/code/km-wpe-startup-handoff-20260913`，分支 `codex/wp-e-startup-handoff-20260913`。前轮代码 `0b3656c919ddfe6f09db4ed0aa0732a828727a5c` 是该后继的祖先，两者仅六份文档变化，产品、测试及脚本无差异。原交付树干净，主仓库既存修改和未跟踪材料保留。

原包 SHA256 `46cd9dce11acf2b11b429f3745924eb43734ec76a842bb76a026af8ff3b57254` 实时匹配；包内 manifest 的 216 个文件 size/hash 全部匹配，唯一未列入文件是 manifest 自身。受控模板 SHA256 `f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b` 匹配，模板不改。

当前源码验证器实测：233/233 新证据、380/380 可携材料、49/49 原生最终材料、34/38 去重材料及 26/26 交接文件匹配；四个历史 Word 锁文件仍 MISSING。封存策略完整校验 270 个成员，未扩大排除。上述为完整性检查，不是原生 Word 或资格 PASS。WP-C 四类历史 native 双 RED 仍 UNMET。

原始核验记录保存于 `/home/ywyz/code/wp-e-startup-coordination-20260913/preservation-before.json` 和 `sealed-integrity-before.json`。新材料另存，不覆盖旧包或旧证据目录。

## 执行与证据角色

原定 Codex 负责整合、实际 diff 和独立复验；本地 OpenCode 实现产品代码、测试和辅助脚本，固定 CLI 1.18.30、`opencode-go/glm-5.3-flash`。首次三个默认协调子代理在启动时遇到额度限制，未执行或写入；随后使用已配置的其他子代理角色继续，没有切换 OpenCode provider、模型或付费方案。

OpenCode 按逐轮任务书、绝对路径、明确权限、`--pure`、JSON 事件及会话 ID 执行；出现503 Forwarding failure（本机 Privoxy SOCKS5 转发不可用）。检查进程、diff及落盘材料后，缩小到最小诊断仍失败，没有切换provider或付费方案。Main已向用户说明按授权的必要接手条款改由Codex实现启动代码，并由luna_worker独立只读复审；辅助脚本先由luna_worker实现，最后由Main修复复审发现，再交另一luna_worker只读审查。全部任务书和事件保存在外部startup-rounds/handoff-rounds目录。

用户随后明确要求移除 Spark 子代理，改用 OpenCode Go 或 `luna_worker`。全局活动配置已删除两份 Spark 代理定义并将默认子代理设为 Luna；本轮后续协调与独立复验使用 `luna_worker`。此前只读 reviewer 已停止，其进程/历史页面核查只作事实线索，不替代恢复后的当前浏览器验收。该开发工具配置变更不属于产品代码或资格配置。

## 当前已执行验证

新增启动入口测试在未修改产品源码时连续两次运行，各为13失败/1通过；相同测试源 SHA256 `dc3a4759b1a1d9ca107f9d6ee7eb2bc94d8951bf826e12a2d714f2bd78a9d6cb` 与原源码/日志已保留。主要失败是普通启动忽略运维资格配置；不是缺少模块或导入错误。最小修复后14项通过，后续新增配置和依赖负向覆盖独立记账，不回填为此前RED。

启动/资格/真实渲染/布局/封存策略适用集93通过，其中包含真实SQLite保存版本渲染。Foundation261通过、WRITE267通过（38条warning见原日志）。因运行时绑定校验被复用到启动，另在专属回环 MySQL8.4.11/READ COMMITTED、临时存储容器复验真实保存渲染与超页缩减链路2项，均通过；容器已停止。没有数据库schema或事务算法修改，没有生产数据库连接。

所有本轮测试、候选及浏览器数据为隔离合成材料或mock边界。真实应用AI、云端/远端CI、Windows原生、正式资格安装尚未执行。当前源 hash 集合复核一致，全量普通测试1800通过、1跳过、12条warning；独立交接验证器测试15通过。Foundation/WRITE单独运行，未合并虚增计数。前轮通过仅保留为历史。

## 浏览器候选决策

旧合成服务器 PID1869693、端口18778仍属于前轮工作树，没有重启或重seed；默认18777服务已停止。当前Edge新标签页已读取真实`/weekly-plan`，合成长文计划6仍为version12/revision2，日期2026-09-14至18，实测2页。

旧候选无可获取ID，只有超过TTL的时间线，未实际触发旧候选TTL拒绝；不能写成该项通过。正常页面重新检测后显式请求一次候选，当前周期请求1、失败0；旧周期历史请求1保留。当前提案26字段，每字段十次“围绕主题进行观察，”→“围绕主题观察，”，数字后缀和7名称保持；33个长文结构字段之外的10个每日字段亦不变。日期、主题、人员与条数保持。Main已经展示具体差异并请求明确决定，目前待答复，未采用/保存/下载，不记采用后分支PASS。

当前浏览器运行的是前轮代码，必须按该证据角色记录；不能冒充尚未冻结的新代码浏览器PASS。原始4长文和已采用4去重长文未改动。

## CI和运行环境

本地实际环境为LibreOffice26.2.5.2 620(Build:2)、Poppler26.01.0；原有SimSun字体SHA256 `1526ac24375f51f6eb73bc2d3f8072dbe4a80a3a65217677c9d9a84f67dab2ab`，仅使用进程级FONTCONFIG_FILE保持可见，未复制或安装字体。

Quality workflow固定基础runner为Ubuntu24.04，并从其公开APT源安装`libreoffice-writer/poppler-utils/fontconfig`、输出实际包与工具版本；测试前明确检查SimSun，缺失即失败，不跳过真实渲染测试。已通过本地YAML解析和各run段`bash -n`、本机字体前置核验。未执行远端job；公开APT源更新未冻结为历史快照，不声称其版本或渲染结果等同本机。runner合法宋体供应仍是未解决前置条件。

来源：[Ubuntu LO包](https://packages.ubuntu.com/noble/libreoffice-writer)、[Ubuntu Poppler包](https://packages.ubuntu.com/noble/poppler-utils)、[Microsoft字体再分发说明](https://learn.microsoft.com/en-us/typography/fonts/font-faq)。字体文件不进入仓库、Git bundle或交接包。
