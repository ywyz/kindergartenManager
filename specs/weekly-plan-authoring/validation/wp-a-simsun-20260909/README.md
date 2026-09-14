# 可携带的WP-A合成验证样本

此目录仅用于Office兼容性和排版验证，不是产品导出、用户教案或已合格模板。
九份DOCX、九份历史Linux PDF和十二页PNG逐项匹配2026-09-09原manifest的SHA256。
字体二进制、运行缓存及业务数据没有收入此目录。

- `samples/`：在Windows Word中只读打开，输出到另一个本轮目录。
- `linux-reference/`：历史LibreOfficeDev26.8 alpha + SimSun结果，只作参照。
- `manifest.json`：本目录相对路径/hash清单；可跨平台核验。
- `historical-linux-manifest.json`、`historical-linux-report.md`：原样历史记录，绝对路径只描述当时环境。
- `historical-linux-scripts/`：原样保存的生成/检查脚本，需要Linux原环境；不要在Windows直接运行或将路径替换后覆盖样本。

执行 `py -3 specs/weekly-plan-authoring/validation/verify_wp_a_bundle.py` 校验；
Windows详细任务见 `../../WP-A-Windows-validation-prompt.md`。

`.gitattributes`对本目录禁用文本换行转换，以保持历史脚本/报告及二进制逐字节hash。
本次没有重新生成或重新渲染样本，不产生新的Office通过结论。
