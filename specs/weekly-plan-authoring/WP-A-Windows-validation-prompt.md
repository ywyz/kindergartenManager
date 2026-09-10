# WP-A Windows Word 验证提示词

以下正文可直接交给Windows上的执行代理。

---

请在Windows上执行 kindergartenManager Issue #77 的 **WP-A Windows Word 排版验证子门**。
本次只验证合成排版候选和形成证据；不启动产品开发，不做真实库迁移或部署。

## 1. 实时核对和保护基线

从GitHub获取 `handoff/wp-a-windows-20260910` 分支；不要只拉main（本次交接尚未合并main）。
先执行git status、fetch、rev-parse HEAD，记录实际handoff_sha；有本机改动则另建隔离worktree，不reset/覆盖。
不要猜Linux绝对路径在Windows有效，也不要自动执行历史Linux脚本。

实时读取#77/#75正文与回写、AGENTS.md、ADR-0011，以及：
- `specs/weekly-plan-authoring/spec.md`、`tasks.md`、`calendar-contract.md`、`service-contract.md`、`migration-proposal.md`；
- `evidence/WP-A-20260908.md`、`review.md`、`WP-A-fonts-20260909.md`、`layout-simsun-20260909.md`；
- `evidence/WP-B-20260910.md`、`WP-C-20260910.md`和对应独立Review；
- `validation/wp-a-simsun-20260909/README.md`与两个manifest。

代码祖先包括WP-B `41b63c9cf6492d31c91faa07bd021e4096eb5379`及WP-C身份子步
`00afdc878b306475508c777997956cdf4638dbef`。这是交接代码来源，不是Word tested_code_sha。
历史Linux样本生成依据`8dcc83376577695b562529ec42adc6b48817f004`；本次对同样本的新客户端实测
应记录handoff_sha、各DOCX SHA256、Word环境及本轮结果，不篡改历史运行的SHA/时间/manifest。
CI只认实际headSha和具体检查；找不到则记未取得，不能由本地通过推导CI成功。

## 2. 校验可携带样本

在仓库根运行（只需Python标准库，不需要启动应用）：

```powershell
py -3 specs/weekly-plan-authoring/validation/verify_wp_a_bundle.py
```

如果Python不可用，用PowerShell Get-FileHash逐项核对manifest；不要仅凭文件名认定同一样本。
任一缺失/hash不符立即停止该样本验证并列明差异，不用重新生成文件覆盖原件。
`validation/wp-a-simsun-20260909/samples/`含九份**合成验证fixture**；`linux-reference/`是同一DOCX的
历史Linux PDF/PNG参照，不是Windows结果，也不是正式产品导出。

不修改`templates/weekplan.docx`、正式exporter、模板hash/profile/binding。源码模板hash应仍为
`f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b`。
历史模板是双表；本轮验证的是独立单表五/六列候选，不能直接授予正式模板资格。

## 3. 验证Windows真实环境

先确定Microsoft Word桌面版是否安装、可启动且可操作，记录Windows版本、Word产品/版本/build/位数、
兼容模式、默认打印机/纸张、缩放、区域设置；只记录技术信息，不收集Office账号或产品密钥。
确认Word实际使用宋体/SimSun，无替代字体；记录字体文件版本/hash，字体二进制不入仓。
Windows字体hash可能与Linux不同：据实记录差异，不通过替换字体文件伪造一致。

使用现有可用的Word自动化或COM读取、重新分页及导出PDF；必须实际打开DOCX确认没有修复/兼容警告。
只读打开或操作专属副本，禁止覆盖九份输入、批量另存导致原hash变化。
缺Word、无法控制/实际观察或字体替代，准确记BLOCKED；LibreOffice/浏览器预览/Python解析不冒充Word。
若当前工具无法读取原生Word画面，说明实际可验证到哪一步，保留Word导出的PDF逐页图，
并请求用户补充必要的Word实际打开/打印预览观察，不能仅凭COM对象创建成功声称完整验收。

## 4. 九份样本逐一验证

| 形态 | 最短完整 | 长中文 | 缩减候选 |
|---|---|---|---|
| 五天 | normal-five-short.docx | normal-five-long.docx | normal-compact-candidate.docx |
| 前置周日六天 | preceding-sunday-six-short.docx | preceding-sunday-six-long.docx | sunday-compact-candidate.docx |
| 周六六天 | saturday-six-short.docx | saturday-six-long.docx | saturday-compact-candidate.docx |

2026-09-09历史Linux的结果是short/compact各1页、long各2页；不能把这个表当本次预期结果强行凑齐。
对每份记录Word实际分页、PDF页数、页面尺寸、字体、每页图和人工/独立视觉结论。
页数与视觉必须分别验证：一页但有裁切/重叠仍失败；长文两页必须明确记“单页失败”，不能省略第二页。

核对：
- A4纵向，11906×16838 twips；边距左右720、上下284；表格总宽10466 twips，边框处于可打印范围。
- 正文宋体12pt（小四）、固定行距20pt；标题16pt居中加粗保持候选要求；不能降字号/行距凑一页。
- 五天grid `[933,920,1722,1722,1723,1723,1723]`，六天grid `[933,920,1435,1435,1435,1436,1436,1436]`。
- 五/六个日期列顺序完整、周日/周六合成标识正确；这是合成日期夹具，不宣称真实法定调休或WP-D日历通过。
- 合并单元格、九行结构、右边框/底边框、最后户外游戏行、区域第三条指导、最后家园共育行没有被裁切或隐藏。
- 多教师姓名、长中文、标点/书名号/空格、换行、跨页重复/丢失、表格左右溢出逐项检查。
- 体能大循环固定；集体游戏恰好2、自主游戏1，各3目标；重点区域1、目标3、指导3、材料；
  本周重点3、环境3、生活习惯3、家园共育一段，内容/事实/栏目不能被缩减掉。

优先复用原样本完成第一次测量。发现排版问题时先保存原始失败证据；本次仅允许在专属候选副本
尝试必要的几何调整并完整记录差异，不改源模板/产品。需要改变字号、行距、固定数量或产品契约时停止并报告。
compact仅是历史合成缩减候选，不代表用户确认采用或产品AI缩减流程通过。

## 5. 证据与独立Review

在独立本轮目录保存Word导出的PDF、全部逐页PNG、必要Word实际打开/打印预览截图、
每份输入/输出SHA256、客户端环境、运行命令、页数与固定结构检查结果。
禁止把历史Linux PDF改名为Windows证据；禁止删除失败样本、补造时间/截图/CI。
等待用户确认/渲染时不打开应用数据库事务；本任务完全不需业务数据库。

新建 `specs/weekly-plan-authoring/evidence/WP-A-Windows-<实际日期>.md` 与对应manifest，
表格分别记录每份样本：input hash、Word页数、PDF页数、字体是否确认、裁切/溢出、固定数量、结论/理由、证据路径。
记录handoff_sha与本轮evidence_closure_sha（若提交），两者不互换。
调用只读reviewer，不递归委派，不撤销他人修改；逐页独立复核，不能仅审Markdown就给版式PASS。
缺代理/视觉能力据实记缺，不捏造独立Review。任何修正先保留失败，再重验受影响样本。

结论区分：Windows Word子门、目标稳定LibreOffice子门、WP-A整体、正式模板资格、产品/云端验收。
当前历史Linux是LibreOfficeDev26.8 alpha，不能冒称目标稳定版证据；仅完成Windows不足以自动关闭全部缺项。
长文仍两页时保留失败；可报告短样本/compact可行性，不宣称所有长度都可单页。
共享业务RED已移交WP-C；WP-C身份子步GREEN不替代共享/来源，也不替代本轮Office验证。

只在证据完整后回写#77并读回核对，保留未完成项；不关闭#77/#57/#75，不创建PR、发布、部署，
不实施WP-C后续、WP-D/E/F、月计划、Agent能力、正式周exporter或模板资格迁移。
最后列本轮真实结果、仍缺项和下一步提示词。
