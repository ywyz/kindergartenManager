---
applyTo: "app/integration/word_export/**"
---

# Word 文档导出约定

## 技术选型

- **主方案**：`python-docx`（直接操控 Open XML，支持精准表格定位与字体颜色）
- **备方案**：`docxtpl`（仅在主方案无法满足模板需求时切换，需说明理由）

## Word 模板表格结构（固定，不得自行发明字段）

| 行 | 左列（标题） | 右列（填充内容） |
|----|------------|--------------|
| 1 | 第( )周 | （整行合并） |
| 2 | 月 日 周() | （整行合并） |
| 3 | 晨间活动 | 体能大循环/集体游戏/自选游戏 + 重点指导/活动目标/指导要点 |
| 4 | 晨间谈话 | 谈话主题 + 问题设计 |
| 5 | 集体活动 | 活动主题/活动目标/活动重点/活动难点/活动过程 |
| 6 | 室内区域活动 | 游戏区域 + 重点指导/活动目标/指导要点 + 支持策略 |
| 7 | 户外游戏活动 | 游戏区域 + 重点指导/活动目标/指导要点 + 支持策略 |
| 8 | 一日活动反思 | （空白，留用户手填） |

## 差异红字标注

仅"活动过程"字段需要比对标红：

```python
from docx.shared import RGBColor

# 差异段落标红
run.font.color.rgb = RGBColor(0xFF, 0x00, 0x00)
```

比对逻辑：
1. 取 `process_original`（AI 拆分原文）与 `process_adapted`（年龄适配改写文）
2. 逐句/逐段 difflib 比对，仅将**改写文中与原文不同的部分**标红
3. 未改动部分保持默认黑色

## 中文字体

```python
from docx.shared import Pt
from docx.oxml.ns import qn

run.font.name = '宋体'
run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
```

不显式指定字体名时中文字体可能出现乱码，必须处理。

## 导出文件命名

```
{tenant_id}_{user_id}_{年级}_{班级}_{日期YYYYMMDD}_日计划.docx
```

导出文件保存到 `exports/` 目录，并将路径记录到数据库 `export_records` 表。
