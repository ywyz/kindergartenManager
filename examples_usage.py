"""
kg_manager 使用示例
"""

from pathlib import Path
from datetime import date
import kg_manager as kg


def example_basic_workflow():
    """基本工作流示例"""
    print("=" * 60)
    print("示例 1: 基本工作流")
    print("=" * 60)
    
    # 1. 验证教案数据
    plan_data = {
        "晨间活动": {
            "集体游戏": "捉迷藏",
            "自主游戏": "建构区",
        },
        "晨间活动指导": {
            "重点指导": "安全",
            "活动目标": "提升能力",
            "指导要点": "控制速度",
        },
        "晨间谈话": {
            "话题": "天气",
            "问题设计": "今天天气怎样？",
        },
        "集体活动": {
            "活动主题": "美术课",
            "活动目标": "创意",
            "活动准备": "彩笔",
            "活动重点": "想象力",
            "活动难点": "协调",
            "活动过程": "导入-示范-操作",
        },
        "室内区域游戏": {
            "游戏区域": "阅读区",
            "重点指导": "合作",
            "活动目标": "语言",
            "指导要点": "倾听",
            "支持策略": "提示",
        },
        "下午户外游戏": {
            "游戏区域": "操场",
            "重点观察": "规则",
            "活动目标": "协调",
            "指导要点": "交接",
            "支持策略": "示范",
        },
        "一日活动反思": "幼儿配合度高",
    }
    
    errors = kg.validate_plan_data(plan_data)
    if errors:
        print("验证错误:")
        for err in errors:
            print(f"  - {err}")
    else:
        print("✓ 教案数据验证通过")
    
    # 2. 保存学期信息
    db_path = Path("examples/semester.db")
    start = date(2026, 2, 23)
    end = date(2026, 7, 10)
    kg.save_semester(db_path, start, end)
    print(f"✓ 学期信息已保存：{start} - {end}")
    
    # 3. 加载最新学期
    latest = kg.load_latest_semester(db_path)
    if latest:
        print(f"✓ 最新学期：{latest[0]} - {latest[1]}")
    
    # 4. 保存教案到数据库
    plan_db = Path("examples/plan.db")
    plan_date = "2026-02-26"
    kg.save_plan_data(plan_db, plan_date, plan_data)
    print(f"✓ 教案已保存：{plan_date}")
    
    # 5. 加载教案
    loaded = kg.load_plan_data(plan_db, plan_date)
    if loaded:
        print(f"✓ 教案已加载：{plan_date}")
    
    # 6. 列出所有教案日期
    dates = kg.list_plan_dates(plan_db)
    print(f"✓ 数据库中的教案日期：{dates}")
    
    # 7. 计算周次
    week_no = kg.calculate_week_number(start, date.fromisoformat(plan_date))
    print(f"✓ 周次：第（{week_no}）周")
    
    # 8. 生成周次和日期文本
    week_text = kg.build_week_text(week_no)
    date_text = kg.build_date_text(date.fromisoformat(plan_date))
    print(f"✓ 周次文本：{week_text}")
    print(f"✓ 日期文本：{date_text}")


def example_ai_split():
    """AI拆分示例"""
    print("\n" + "=" * 60)
    print("示例 2: AI拆分集体活动")
    print("=" * 60)
    
    draft = """
    活动名称：小班美术《彩色雨点》
    
    活动目标：
    1. 体验点画技法
    2. 感受不同颜色的美感
    3. 培养创意思维
    
    活动准备：
    各种颜色的彩笔或水彩笔、白纸、围裙、湿毛巾等
    
    活动重点：
    掌握点画的基本节奏和技法
    
    活动难点：
    不同颜色的协调搭配
    
    活动过程：
    （1）导入：播放雨点音乐，观看图片，引出活动
    （2）示范：教师演示点画方法
    （3）操作：幼儿自由创作
    （4）分享：展示作品，互相评价
    """
    
    try:
        # 推荐方式：通过参数传递配置（更安全，不会影响全局状态）
        # result = kg.split_collective_activity(
        #     draft,
        #     api_key="your-api-key",
        #     base_url="https://api.openai.com/v1",  # 可选
        #     model="gpt-4o-mini"  # 可选
        # )
        
        # 兼容方式：从环境变量读取（需要设置 OPENAI_API_KEY）
        result = kg.split_collective_activity(draft)
        if result:
            print("✓ AI拆分结果:")
            for key, value in result.items():
                print(f"  {key}: {value[:50]}...")
        else:
            print("✗ AI返回格式不正确")
    except Exception as e:
        print(f"✗ AI处理失败：{e}")
        print("  (需要设置 OPENAI_API_KEY 环境变量或传递 api_key 参数)")


def example_export_schema():
    """导出Schema示例"""
    print("\n" + "=" * 60)
    print("示例 3: 导出教案字段Schema")
    print("=" * 60)
    
    schema_path = Path("examples/example_schema.json")
    kg.export_schema_json(schema_path)
    print(f"✓ Schema已导出：{schema_path}")


def example_word_operations():
    """Word操作示例"""
    print("\n" + "=" * 60)
    print("示例 4: Word文档操作")
    print("=" * 60)
    
    # 使用常量
    print(f"✓ Word字体：{kg.WORD_FONT_NAME}")
    print(f"✓ Word字体大小：{kg.WORD_FONT_SIZE}pt")
    print(f"✓ 首行缩进：{kg.WORD_INDENT_FIRST_LINE}pt")


if __name__ == "__main__":
    example_basic_workflow()
    example_ai_split()
    example_export_schema()
    example_word_operations()
    print("\n" + "=" * 60)
    print("示例完成！")
    print("=" * 60)
