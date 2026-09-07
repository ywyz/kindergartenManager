---
applyTo: "app/integration/word_export/**"
---

# Word 文档导出约定

## 技术选型

- **主方案**：`python-docx`（直接操控 Open XML，支持精准表格定位与字体颜色）
- **备方案**：`docxtpl`（仅在主方案无法满足模板需求时切换，需说明理由）

## 每日计划模板结构（仅适用于对应模板）

以下表格与差异标红约定用于每日计划模板，不应套用到观察、倾听等其他导出。具体字段、反思内容与布局以当前模板、用例和测试为准。

下表概括逻辑栏目，不是模板的物理行号。`templates/teacherplan.docx` 当前为 19 行，子字段分别填入对应单元格；位置映射见 `app/integration/word_export/exporter.py`。

| 栏目 | 左列（标题） | 右列（填充内容） |
|----|------------|--------------|
| 1 | 第( )周 | （整行合并） |
| 2 | 月 日 周() | （整行合并） |
| 3 | 晨间活动 | 体能大循环/集体游戏/自选游戏 + 重点指导/活动目标/指导要点 |
| 4 | 晨间谈话 | 谈话主题 + 问题设计 |
| 5 | 集体活动 | 活动主题/活动目标/活动准备/活动重点/活动难点/活动过程 |
| 6 | 室内区域活动 | 游戏区域 + 重点指导/活动目标/指导要点 + 支持策略 |
| 7 | 户外游戏活动 | 游戏区域 + 重点指导/活动目标/指导要点 + 支持策略 |
| 8 | 一日活动反思 | 已保存的 `daily_reflection`；无内容时留空 |

## 差异红字标注

仅"活动过程"字段需要比对标红：

```python
from docx.shared import RGBColor

# 差异段落标红
run.font.color.rgb = RGBColor(0xFF, 0x00, 0x00)
```

比对逻辑：
1. 取 `activity_process_original`（AI 拆分原文）与 `activity_process_adapted`（年龄适配改写文）
2. 通过 `app/service/diff_service.py` 按句比对，仅将**改写文中新增或修改的句子**标红；已删除原句不输出
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

导出目录、命名与记录持久化按对应用例的当前契约；不要为套用此说明新增表或写入。Word/LibreOffice 是文档兼容性客户端，不是应用运行环境。
