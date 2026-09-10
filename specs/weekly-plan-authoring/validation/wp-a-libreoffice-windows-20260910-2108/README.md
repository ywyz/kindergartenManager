# Windows LibreOffice实测产物

9PDF/12PNG由LibreOffice26.8.0.3本次实际生成，非Word/Linux历史文件。全部输入hash保全。
命令：`uv run --no-project --python 3.14 python -X utf8 specs/weekly-plan-authoring/validation/wp-a-libreoffice-windows-20260910-2108/measure.py`。
诊断：同目录inspect_outputs.py，以uv --with pymupdf --with fonttools执行；完整导出/渲染命令及返回值见run.json。

所有样本行距检测FAIL：源固定20pt，选定连续正文行基线16.9pt。保留失败，不改候选。

- [normal-compact-candidate PDF](normal-compact-candidate/normal-compact-candidate.pdf)：[1页](normal-compact-candidate/page-1.png)
- [normal-five-long PDF](normal-five-long/normal-five-long.pdf)：[1页](normal-five-long/page-1.png)、[2页](normal-five-long/page-2.png)
- [normal-five-short PDF](normal-five-short/normal-five-short.pdf)：[1页](normal-five-short/page-1.png)
- [preceding-sunday-six-long PDF](preceding-sunday-six-long/preceding-sunday-six-long.pdf)：[1页](preceding-sunday-six-long/page-1.png)、[2页](preceding-sunday-six-long/page-2.png)
- [preceding-sunday-six-short PDF](preceding-sunday-six-short/preceding-sunday-six-short.pdf)：[1页](preceding-sunday-six-short/page-1.png)
- [saturday-compact-candidate PDF](saturday-compact-candidate/saturday-compact-candidate.pdf)：[1页](saturday-compact-candidate/page-1.png)
- [saturday-six-long PDF](saturday-six-long/saturday-six-long.pdf)：[1页](saturday-six-long/page-1.png)、[2页](saturday-six-long/page-2.png)
- [saturday-six-short PDF](saturday-six-short/saturday-six-short.pdf)：[1页](saturday-six-short/page-1.png)
- [sunday-compact-candidate PDF](sunday-compact-candidate/sunday-compact-candidate.pdf)：[1页](sunday-compact-candidate/page-1.png)
