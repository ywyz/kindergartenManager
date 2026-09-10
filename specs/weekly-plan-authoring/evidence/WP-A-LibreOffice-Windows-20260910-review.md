# Windows LibreOffice 独立只读Review

2026-09-10，main整合closure_review实际返回；不递归委派、未修改作者文件。Reviewer逐张看完全部12页PNG，并独立用PyMuPDF提取九份正文行基线。

九份均未见左右溢出、文字重叠、裁切、缺失右/下边框或隐藏末家园共育行。五/六日期顺序完整，固定数量完整。
六份short/compact各1页；三份long各2页，单页FAIL。

- normal-five-long：第1页至本周重点1，左标签“本周”；第2页续“重点”及重点2–3，标签被拆页但未丢失。
- preceding-sunday-six-long、saturday-six-long：区域指导3句尾跨页，第2页续“的记录。”，随后重点、环境、习惯、家园共育完整。Reviewer摘要对p1末尾“的”有笔误，main依据原图/逐页文本统一只记录p2明确续句，未改输出。
- normal-five-short、normal-compact-candidate：周一至周五、末户外行、区域指导3、家园共育完整。
- preceding-sunday-six-short、sunday-compact-candidate：周日至周五六列及末行完整。
- saturday-six-short、saturday-compact-candidate：周一至周六六列及末行完整。

关键独立结果：所有九份所检查户外连续正文行基线约16.9pt；源XML固定20pt，Word对照约19.92–20.07pt。
因此九份均rendered line-spacing FAIL，不能因一页和无裁切给总体PASS。空格字体按用户要求不限制。

每次转换exit0且生成有效PDF，但stderr有 `Could not find platform independent libraries <prefix>`，run.json原样保留；未证明其与行距问题有因果关系。
范围仅Windows LibreOffice26.8.0.3 headless PDF rendering，不冒称Linux或原生UI警告/打印预览验收。main生成并重算manifest，未冒称reviewer独立重算所有新增文件hash。
