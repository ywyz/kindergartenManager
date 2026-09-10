# 2026-09-10 收口保全与验证

`prior-Word-manifest.json` / `prior-LibreOffice-manifest.json` 是本轮入口的原字节快照。
其活文档/脚本路径绑定的是当时版本；当前清单已随收口说明和机械 lint 修正更新，不能递归把 prior 清单当当前清单。
三个 `original-scripts/*.py.txt` 保留实际生成/检查 Office 证据时的脚本原字节及原 hash。
对应原路径脚本仅修正 import、UTC alias、等价 set comprehension、显式 `check=False`，没有重新执行。
全部 DOCX/PDF/PNG 输入输出保持原 hash；完整记录见[收口账本](../../evidence/WP-A-closure-20260910.md)。

只读核验（不重渲染、不写输入输出、不启动产品）：

```text
python specs/weekly-plan-authoring/validation/verify_wp_a_bundle.py
python specs/weekly-plan-authoring/validation/verify_wp_a_closure.py
python specs/weekly-plan-authoring/validation/verify_wp_a_closure.py --revision HEAD
python specs/weekly-plan-authoring/validation/verify_wp_a_closure.py --revision HEAD --pdf
```

最后一项需 PyMuPDF。主代理本轮用 Python 3.14.6；远端 Quality 使用 workflow 配置的 Python 3.14.7。
核验 manifest bytes/SHA256、9份样本页数矩阵和21张原生截图索引，不替代已经记录的独立人工格式 Review。
`--revision` 校验 Git 对象，避免只在 Windows 工作树检查正确却在仓库中因换行转换失配。

此目录不包含个人 Office profile、字体二进制、数据库、密钥或真实业务导出。
固定 SHA 的可访问证据链接在提交并 push 后记录于 #77 收口评论。
