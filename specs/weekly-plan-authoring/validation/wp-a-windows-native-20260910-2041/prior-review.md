# WP-A Windows 独立只读 Review

2026-09-10；main整合独立`closure_review`子代理返回的实际复核结果。
Reviewer不递归、不写文件、不撤销作者修改；本记录由main写入。范围为本轮合成候选及证据，不是产品Review 0/0。

## 逐页视觉复核

Reviewer实际用view_image打开本轮9份样本的全部12张PNG，不以Markdown或页数代替视觉判断。
共同结果：表格左右无溢出、右/底边框完整，未见裁切/叠压；标题、多姓名、书名号、标点、换行可见。
五/六日期顺序完整；户外末行、区域指导3及家园共育末行均完整。以下仅为PDF候选视觉判断。

| 样本 | 实际查看 | 结论 |
|---|---|---|
| normal-five-short | page-1.png | 1页，固定栏目/数量完整；单页PDF可行 |
| normal-five-long | page-1.png、page-2.png | 2页均完整；**单页FAIL** |
| normal-compact-candidate | page-1.png | 1页，固定数量完整；仅合成compact可行 |
| preceding-sunday-six-short | page-1.png | 1页，周日—周五六日期、边框和固定数量完整 |
| preceding-sunday-six-long | page-1.png、page-2.png | 2页均完整；**单页FAIL** |
| sunday-compact-candidate | page-1.png | 1页，周日—周五六列、固定数量及末行完整 |
| saturday-six-short | page-1.png | 1页，周一—周六六日期、边框和固定数量完整 |
| saturday-six-long | page-1.png、page-2.png | 2页均完整；**单页FAIL** |
| saturday-compact-candidate | page-1.png | 1页，周一—周六六列、固定数量及末行完整 |

首次口头汇总误把五列long的材料行归到第二页；main指出后reviewer再次确认并更正：

- 五列long第1页含区域目标1–3、材料及“指导：”，第2页从指导1开始。
- 周日六列long第1页结束于区域目标3“……尊重同伴作品。”；第2页从材料行开始，再为指导1–3。
- 周六六列long与周日六列相同。

三份第二页继续周总结与家园共育，左侧合并标签不重复显示；没有发现正文丢失/重复。
全部页保留，未用裁掉第二页制造单页。

## 独立hash与结构复核

Reviewer重新计算9份输入DOCX与9份PDF的SHA256，全部与word.json一致；不只是读取作者的PASS标记。
核对inspection.json：单表九行、总宽10466、两种grid、A4 595.32×841.92pt均一致。
固定结构全部为体能大循环、集体2/自主1各3目标、区域1/目标3/指导3/材料、重点3/环境3/习惯3/家园1。
PDF非空白字符多重集与源相同，missing/extra均空；此检查不代替顺序/空格保真/视觉审查。
PNG清单hash由main manifest生成，reviewer此次逐页视觉和PDF/DOCX重算分开记录，不冒称独立重算全部PNG。

## 字体与未关闭限制

Reviewer确认所有PDF可见非空span为SimSun，正文12pt，标题15.96pt；对应源XML为12/16pt。
非空XML run均宋体，非空段落固定20pt。PDF仍包含TimesNewRomanPSMT 10.56pt纯空格：
五列各23个、六列各26个。**不能写“PDF仅宋体”或“全文无替代字体”**；严格全span纯宋体未通过。
不认定这些空格已是经证明的可豁免段末标记，也不要求修改字号/行距去凑证据。
COM整表9999999及空字体名属混合/未定义读数，不作为格式PASS。

原生Word画面工具三次pipe失败，用户答应稍后补观察；reviewer没有观察修复/兼容/字体替换警告或原生打印预览。
因此Word PDF视觉可行性结论不解除Windows完整子门BLOCKED。未虚构截图或人工观察。

## 门边界结论

WP-A tasks的最短完整排版可行性与#77最终正常/长中文单页验收应分开：本轮最短五/六列PDF可容纳全部结构，
但long三份均失败，不能宣称所有长度都单页。原生Word观察、严格字体范围及目标稳定LibreOffice尚缺，WP-A总门不PASS。
历史LibreOfficeDev26.8 alpha仅作历史参照；正式模板资格归WP-E/#56；产品/云端门未执行。

证据保全后可以返回Ubuntu，按WP-C-next-prompt.md在另次授权下推进共享授权/实际教学日事实小步，先真实RED再GREEN；
不以WP-C身份子步GREEN替代共享/来源，也不把平台切换记为WP-A关闭。本轮没有产品开发、迁移或部署。

## 最终证据清单窄复核

Reviewer随后独立重算manifest当时所列75项的hash/大小及路径，9输入/9PDF/12PNG均一致，报告、字体限制、
修正后的跨页描述和各门状态未发现具体偏差。该复核发生在追加本段之前；本段仅记录返回结果，
main追加后更新manifest中文档hash，不改任何DOCX/PDF/PNG。
