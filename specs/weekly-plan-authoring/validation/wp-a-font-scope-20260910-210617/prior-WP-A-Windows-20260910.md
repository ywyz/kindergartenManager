# WP-A Windows Word 子门：2026-09-10

本轮完成九份原合成样本的 **Microsoft Word COM 实际重新分页、9 PDF、12 页 PNG、输入保全及独立逐页视觉复核**。
short/compact 各1页；long 各2页，明确单页失败。**Windows Word 子门仍 BLOCKED（严格字体确认未闭合）**。晚间重试已恢复原生画面工具，
九份只读副本实际打开未见修复/兼容警告，12页打印预览全部观察并保存21张原生截图。
原生观察缺项已补齐；这不等于已证明全文（含空白）无字体替代。
WP-A整体不关闭。目标稳定LibreOffice、正式模板资格、产品/云端各门未由本轮通过。

## 基线、来源与证据身份

- 实测环境日期：2026-09-10，Asia/Shanghai。Word运行窗口为12:09:30–12:09:47（+08:00），逐份精确时间见word.json。
- 初始`git status --short`为空；没有本地修改，故直接使用现有交接分支，没有reset/stash/覆盖。
- `git fetch origin handoff/wp-a-windows-20260910`成功；当前分支同名。
- fetch前/后HEAD、FETCH_HEAD及 **handoff_sha均为`eb3504383023eac6f6c93d8769b6d273a55abd7f`**。
- `git merge-base --is-ancestor`确认WP-B `41b63c9cf6492d31c91faa07bd021e4096eb5379`和
  WP-C身份子步`00afdc878b306475508c777997956cdf4638dbef`都是祖先（exit0）。这不是本轮Word tested_code_sha。
- 历史Linux生成源码`8dcc83376577695b562529ec42adc6b48817f004`、历史时间、manifest及二进制没有改写。
  本轮以handoff_sha + 各DOCX SHA256 + 客户端环境绑定测量，不把历史生成SHA换成本次运行SHA。
- `evidence_closure_sha = null`：本轮尚未提交；不可用handoff_sha冒充证据闭合提交。
- 已实时读取#77/#75正文与全部回写，快照在本轮目录`issue-77-before.json`/`issue-75-before.json`；
  已读AGENTS、ADR-0011、spec/tasks/calendar/service/migration、WP-A与字体/布局历史、WP-B/WP-C及其独立Review、便携README和manifest。
- `py`不可用，按用户授权使用uv安装Python3.14.6；以`uv run --no-project --python 3.14 python .../verify_wp_a_bundle.py`
  实际检查并在Word运行后再验，均`Verified 37 files`。只是完整性，不是Office PASS；没有启动应用或业务数据库。

原正式`templates/weekplan.docx` SHA256仍为
`f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b`。
历史模板双表与当前独立单表候选分开；没有修改模板、exporter、profile/hash/binding、产品代码或迁移。

## Windows / Word / 字体与打印环境

| 项目 | 本轮实际记录 |
|---|---|
| Windows | Windows 11 专业版，10.0.26200 / build26200，64位 |
| Word产品 | Microsoft Word / Microsoft 365；ClickToRun O365HomePremRetail；仅技术产品标识，未读取账号/密钥 |
| 版本 | COM Version16.0 / Build16.0.20326；安装VersionToReport16.0.20326.20132，x64 |
| 兼容/视图 | 九份CompatibilityMode=15；View.Type=3打印布局；Zoom=100%；兼容模式值不等于已观察“无兼容警告” |
| 打印机 | 系统默认及Word ActivePrinter均Brother DCP-T725DW Printer；A4 210×297mm；未实际打印 |
| 区域 | Culture、SystemLocale均zh-CN，时区Asia/Shanghai |
| 宋体 | C:/Windows/Fonts/simsun.ttc；18,316,748 bytes；SimSun及NSimSun Version5.24 |
| 字体SHA256 | `1526ac24375f51f6eb73bc2d3f8072dbe4a80a3a65217677c9d9a84f67dab2ab`，与历史Linux恰好相同；未替换字体，字体二进制未入仓 |
| 原生观察 | 首轮native pipe os error2；晚间新版Computer Use重新初始化后恢复，九份只读打开未见修复/兼容警告，12页预览完整；字体替代不能仅凭无弹窗排除 |

Word以只读方式打开原件，ConfirmConversions=false、AddToRecentFiles=false、OpenAndRepair=false、Visible=true、
DisplayAlerts=-1；实际调用Repaginate、ComputeStatistics及ExportAsFixedFormat（PDF、print quality、全部页面）。
Close/Quit不保存；九份输入前后SHA一致。COM调用没有报告错误不代表已看见/排除全部警告。

PDF实际可见非空白字形均为嵌入 **SimSun**：正文12pt；标题PDF数值15.96pt，源OOXML为16pt加粗居中，未调整字号。
但是五列各有23个、六列各有26个`TimesNewRomanPSMT` 10.56pt纯空格span，详见逐页inspection.json。
因此“可见正文宋体”已确认；**“全文（含空白）仅宋体/无替代”未确认**，不能把该差异隐藏或自行豁免。
COM整表字体/行距读回混合值9999999和空字体名，保留原始读数，不把它作为格式证据。
空格来源是否为段末标记/继承格式需另行确证；当前未改变字体/字号/行距来消除此差异。

## 九份测量矩阵

下表F=可见文字为嵌入宋体，纯空格含Times New Roman、严格全文字体差异尚待核实；
V=独立逐页审图未见裁切/重叠/左右溢出；C=固定数量全部完整，详见下一节。
所有短/compact的“可行”均只指当前合成候选PDF；其Windows完整子门仍待严格字体问题闭合。

| 输入 | input SHA256 | Word/PDF页数 | 字体 | 裁切/溢出 | 固定数量 | 本轮结论/理由 | 证据子目录 |
|---|---|---:|---|---|---|---|---|
| normal-five-short.docx | `7eca517011011b5cb7c3b74d38756fdfef6da5f2a7df44503bceefdbd07593c9` | 1/1 | F | V | C | 单页PDF/原生预览可行；严格字体待核实 | normal-five-short/ |
| normal-five-long.docx | `9cd738dd630228f8d3b3c314742f7f62e16de498904a097407b52edef7597f4f` | 2/2 | F | V（两页） | C | **单页FAIL**；两页完整，非单页通过 | normal-five-long/ |
| normal-compact-candidate.docx | `e6d7a4dbb44418e0078fdd2280fec89bb12f33c0c3aaec67235ab9d1821bb350` | 1/1 | F | V | C | 合成compact单页可行；非用户采用 | normal-compact-candidate/ |
| preceding-sunday-six-short.docx | `78b7f8fdab2714a4cb4a5cacfaba55092229462653811ce66503d61e2ff1109a` | 1/1 | F | V | C | 单页PDF/原生预览可行；严格字体待核实 | preceding-sunday-six-short/ |
| preceding-sunday-six-long.docx | `ff6088b80654fbfdd096b233e995ef1394b9209ea50728ea9b21ce43a4f0c6d6` | 2/2 | F | V（两页） | C | **单页FAIL**；保留第2页 | preceding-sunday-six-long/ |
| sunday-compact-candidate.docx | `45b02145e835b27d54d2ed57aa3a8f2e57bbb13c335b1c0fadd2dcf69288d27a` | 1/1 | F | V | C | 合成compact单页可行；非用户采用 | sunday-compact-candidate/ |
| saturday-six-short.docx | `99bfb2d7be462be4353a5b54affddac60c4bd257040f4a6e237f5bbd58073259` | 1/1 | F | V | C | 单页PDF/原生预览可行；严格字体待核实 | saturday-six-short/ |
| saturday-six-long.docx | `600fc88240d87d03854d4a51c4985b654fb606015dcb1a771f8947f78c74d374` | 2/2 | F | V（两页） | C | **单页FAIL**；保留第2页 | saturday-six-long/ |
| saturday-compact-candidate.docx | `4286ee43ced4a9043231264851c75cb9b1ddf76594294f23a3ac9f85066b69b3` | 1/1 | F | V | C | 合成compact单页可行；非用户采用 | saturday-compact-candidate/ |

证据目录根：[wp-a-windows-20260910-1208](../validation/wp-a-windows-20260910-1208/README.md)。每个子目录包含
同名Word PDF、全部page-N.png、word.json、pdfinfo.txt、inspection.json及逐页文本；输入/输出hash见
[本轮manifest](WP-A-Windows-20260910-manifest.json)。Linux PDF没有复制或改名为本轮证据。

## 结构、几何与视觉核对

- OOXML纸张11906×16838 twips、左右720/上下284、单表九行；COM为595.3×841.9pt、左右36/上下14.2；
  PDF为595.32×841.92pt A4、旋转0。三个读数分别保留，不能用近似值改写输入精确值。
- 五列grid `[933,920,1722,1722,1723,1723,1723]`；六列
  `[933,920,1435,1435,1435,1436,1436,1436]`；tblW和总grid均10466 twips。
- 非空OOXML run均正文24半磅/宋体、标题32半磅/宋体/加粗/居中；非空段落均line400、lineRule exact、前后0。
  没有减字号、行距或几何调整；本轮没有衍生候选或重生成DOCX。
- 默认打印机报告的PrintableArea单位为1/100英寸，换算约x8.4–586.8pt、y8.4–833.28pt；
  PDF表格绘图整体x35.76–559.66pt，最上14.16pt、最下817.32pt，均在此范围内。
  这是驱动几何核对，未冒称实体打印/原生打印预览验收。
- 常规09-07至09-11、前置周日09-06至09-11、周六09-07至09-12，五/六日期按序，三名合成教师可见。
  仅合成日期夹具，不表示真实法定调休或WP-D日历通过。
- 体能大循环固定；集体游戏2、自主1，各①②③三目标；重点区域1，目标3、指导3、有材料；
  本周重点/环境/生活习惯各3，家园共育一段。输入解析与独立逐页视觉均核对。
- 九份PDF全部页合并后与输入非空白字符多重集一致，无新增/缺字；此诊断不能单独证明顺序、空格保真或无裁切。
  日期顺序、书名号、标点、换行、多姓名、末户外行、区域指导3、末家园行、左右/底边框另由审图检查。
- 长样本跨页保留全部页；五列long第1页到“指导：”，第2页从指导1开始；六列long具体跨页点见独立Review。
  第2页左侧合并标签未重复显示，未把它误报为正文丢失；没有用隐藏第2页制造一页。

## 独立Review与问题保留

用户明确授权子代理；main调用只读`closure_review`，禁止递归及文件修改。Reviewer实际打开全部12页PNG，
逐份输出视觉结论；不是只审Markdown。Main抽核五列short、五列long两页、周日compact，并独立完成字体/文本/几何分析。
详见[独立Review](WP-A-Windows-20260910-review.md)。首次Review不包含原生Word画面；新增21张原生截图另行独立复核，见晚间补充。

失败/限制全部保留：py缺失与uv替代；原生pipe三次失败；首次PDF依赖探测缺模块；只读解析脚本首次
未识别w:br而失败，修正后重跑（未改输入/渲染）；COM混合格式读数；纯空格字体差异；长文两页。
本任务没有应用事务、业务数据库、真实模型请求、迁移、部署、正式周exporter或产品测试。

## CI、关闭判断与下一步

实际handoff headSha `eb3504383023eac6f6c93d8769b6d273a55abd7f`有
[Quality run34469759797](https://github.com/ywyz/kindergartenManager/actions/runs/34469759797)，
具体[Python 3.14 quality检查](https://github.com/ywyz/kindergartenManager/actions/runs/34469759797/job/102846654655)
为completed/**failure**。本轮没有修CI或把本地结果推成CI成功；未取得该SHA的成功CodeQL检查。

| 门 | 本轮状态与下一步 |
|---|---|
| Windows Word子门 | BLOCKED：已有9PDF/12PNG/页数与视觉；原生观察已补齐，待全文字体差异核实；long单页FAIL保留 |
| 目标稳定LibreOffice子门 | 未取得；历史LibreOfficeDev26.8 alpha不替代稳定版，需要同hash样本的新独立测量 |
| WP-A整体 | 暂不能关闭；tasks要求最短完整五/六列目标Office可行性，不能把本轮缺项勾绿 |
| 长文单页/缩减 | 当前long三份失败；compact只证明合成候选可行，不证明事实等价、用户采用或产品AI流程 |
| 正式模板资格 | 未授予，归WP-E/#56；双表旧模板不因独立单表试排取得资格 |
| 产品/云端 | 未执行，WP-C身份GREEN不替代共享/来源，WP-D/E/F另门 |

**可以切回Ubuntu继续后续已授权的开发小步，无须把WP-A虚假关闭。** 切换前保全/传递本轮新证据，
Ubuntu重新fetch交接分支并检查本机改动；不能只取尚未包含交接的main。下一产品工作须另按
`WP-C-next-prompt.md`授权，先真实shared_weekly_v1授权/实际教学日事实接口的RED，再对应最小GREEN；本轮未实施。
WP-A是最短完整排版可行性门；long两页必须继续作为负向结果保留，不能据此声称所有长度可单页，
也不应把后续产品缩减/正式模板资格提前塞成本轮实现。

下一步提示词：

> 续接WP-A-Windows-20260910账本，原生只读打开及12页打印预览已补齐，继续严格字体核实，
> 保留9PDF/12PNG和long单页FAIL。核实纯空格Times New Roman差异，不改原件、字号或行距。
> 之后在Ubuntu目标稳定LibreOffice上对同hash九份样本独立渲染/逐页Review；补齐后再判断WP-A可行性门，
> 不外推正式模板或产品/云端。若转开发，另按WP-C-next-prompt.md只推进共享授权/实际教学日事实小步，先RED再GREEN。

## GitHub回写

尚未回写#77：本次先完成原生工具恢复与截图补充；严格字体确认仍未完成，不将完整Windows子门写成PASS。
没有关闭#77/#57/#75、创建PR、发布或部署。补充后应更新本报告/manifest，独立复核，再回写#77并读回核对。

## 晚间原生画面重试补充

2026-09-10 20:44–20:52（+08:00）记录九份实际只读打开与12页打印预览。
使用computer-use 26.903.71938，通过受支持的 `@oai/sky` 初始化、list_apps/list_windows、get_window_state、
press_key及截图定位操作。此前26.825.32147的native pipe失败记录保留；本次重新初始化后连接成功。
没有修改代理、注册表或系统网络设置，未取得代理导致此前故障的证据，不能断言根因。

原始九份DOCX复制至专属inputs并设置只读；没有编辑、另存、重新导出PDF或实际打印。
打开视图100%，打印预览适合整页81%，Brother打印机就绪、每版1页；三份long的两页分别保存。
所有样本未见修复/转换/兼容警告，标题显示只读；这只描述本次打开的可见行为。
PDF的纯空格Times New Roman差异仍保留，不以没有字体警告豁免。

[原生补充记录与21张截图](../validation/wp-a-windows-native-20260910-2041/README.md)；
`observations.json`记录截图保存时刻，不伪称精确打开时刻。旧报告/manifest快照保留于补充目录，历史Linux证据未改。
