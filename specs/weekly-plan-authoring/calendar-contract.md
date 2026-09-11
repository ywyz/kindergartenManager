# 2026-09-11 WP-D 当前日历实现

当前入口为 `CalendarApplication.resolve_week(expected,class_id,semester_id,requested_start,requested_end)` 与 `display_for_scope(expected,scope)`，返回关闭的 `WeekDisplay(scope,facts,week_number,columns,class_name,grade,semester_display,display_rule_version,label_fingerprint)`；每日列为 `DayDisplay(day,teaching,morning_label)`。同一身份事务内复用唯一共享 READ 政策并读取权威学期寒暑假类型、班级和学年。内部 `display_from_facts(repository,facts)` 供已授权事务重验展示指纹，不再开连接。

先解析完整规范五／六列与实际教学日再取源／AI：缩短选择仍为同一 scope 和完整列；前置调休周日归下一周一，周六归本周。跨周、无学期交集、同周跨学期冲突、七列、未知覆盖或矛盾数据失败关闭。整周假期仍计周序，但唯一政策要求 assignment 与实际教学日至少一天交集，因此零教学日整周仍 `scope_denied`；假期标签纯投影与授权是不同证据角色。

锁定包已经是 `chinesecalendar 1.11.0`，不按下方历史“未锁定”文字重复升级。原 v1 日期集合指纹和教学事实序列化不变；独立 holiday-name 数据校验与 `shared-week-display.v1` 指纹覆盖标签变化。学校寒暑假优先于调休：开学前周一标学校假期，其余空；期末后首格标学校假期，其余空。连续法定假期在本周可见段首标节名，即使连续日期节名不同也不重复标；跨周新段重新标。普通周末不标法定假期，调休教学日不因节名而标休假。日历变化提供差异，不后台改历史；采用／保存校验当前标签、版本和掩码。

每日页面现通过 `get_daily_week_number` 和 DatePanel 的显式 resolver 使用相同的前置调休周日规则。每日旧个人学期配置仅是展示输入，不替代共享权威 semester/class 或授予成员权限；其学期外周日不前移。完整候选窗口日历不可用时页面清除可用日期／周次和 Agent scope，显示不可用提示并停止日期依赖加载；其他 DatePanel 调用方、随机日期业务和旧 get_week_number 不变。每日历史已保存的周次快照不后台重算。

最终证据与未满足门见[WP-D 矩阵](WP-D-completion-contract.md)、[本轮证据](evidence/WP-D-20260911.md)和[当前状态](current-status.md)。以下为 WP-A/WP-C 各日期的历史契约，不作为当前尚无实现或整门通过的声明。

---

> 2026-09-11 WP-C完整协作路径已实现；[关闭矩阵](WP-C-completion-contract.md)、[本轮证据](evidence/WP-C-complete-20260911.md)与[当前状态](current-status.md)说明实际覆盖和未完成门。历史阶段描述不代表当前实现缺项。

> 2026-09-11当前实现补充：授权及最小教学日事实见[本轮冻结契约](WP-C-authorization-contract.md)与[交付账本](evidence/WP-C-authorization-20260911.md)。下方WP-A提案按当时时点保留；未实现的共享根/来源及WP-D/E仍不计通过。本步无新schema。

# WP-A 教学周与日期契约

2026-09-08 技术设计；依据 #77 已确认规则，尚未实现。只用于新共享周计划及其每日日期展示。

## 唯一身份与归属

- 学期使用园所管理员的稳定 `semester_id`、实际 `[start_date, end_date]`、开学前/结束后寒暑假类型，
  不读取操作教师的个人 active semester 作为共享权威。学期属于精确 academic_year。
- `anchor_monday(d) = d - timedelta(days=d.weekday())`。教学周主键使用周一日期，不能使用
  ISO week number、显示起止、自然年或教师配置 ID。周次为
  `1 + (anchor_monday - anchor_monday(semester.start_date)).days // 7`，包括整周休假。
- 五个基本列为 anchor 至 anchor+4；按受支持日历判定 anchor-1 的周日调休和 anchor+5 的周六调休。
  前置周日的归属函数固定为次日周一；周六归本周一。anchor+6 的周日永不加入本周。
  七列组合返回 `unsupported_seven_columns`，不裁成六列，不写聚合或日期占用。
- 学期边界优先：不把学期外调休日认作教学日。周一至周五假期列仍存在；六列中的额外周末
  仅在学期内且为法定调休教学日时增加。生成前检查完整候选窗口所需年份，未知即
  `calendar_unavailable`；不得套用现有 `date_service.is_workday()` 的 weekday-only 结果。
- 起止选择必须落在一个规范教学周窗口内，包含的教学日期不得归另一 anchor；解析后显示完整规范列，
  用户确认的是该周。缩短选择范围不缩短存储列，不另分配 identity。反向、跨两个 anchor、完全学期外拒绝。
  前置周日不能被当作上一周的结束日。空假期格也是一个日期，不能属于同班两份新计划。
- 建议另建日期占用表，`UNIQUE(tenant_id, class_instance_id, day_date)`；同一班实例的所有新周根共享
  该约束，不能仅在版本内唯一。版本的重复日期是同一根的历史快照，不能重复登记占用。
  同一自然周横跨两个学期时不得各自动生成一份：若班实例已有日期占用或两个学期均声称该周，返回
  `semester_week_conflict`，由管理员调整权威边界后再创建。本期不合并学期、不转移已有占用。

## 假期优先规则

先冻结规范日期和假期掩码，再查源/调用 AI。假期格的集体活动始终空；后续导入、手填校验、AI 和缩减
均不能破坏掩码。开学首周周一早于开学时标学校寒/暑假，其余开学前日期为空；结束末周首个假期列标
学校寒/暑假，其余为空。法定连续假期按本周可见连续段首日标节名，跨到下周时在下周段首日重新标，
对应 spec 2.3 的“本周假期段第一天”。普通周末不被标成法定节日；调休日期不能因 holiday name 非空
就误判休假。保存日历版本与规则版本；更新日历数据只提示重算差异，不改旧版本。

## 待实现确定性矩阵

| 输入 | 预期 |
|---|---|
| 实际开学 2026-09-02，anchor 08-31 | 第 1 周，周一暑假，周二空，周三开始教学 |
| 上述学期 anchor 09-07 | 第 2 周，不以实际教学天数扣周 |
| 合成调休 09-06，anchor 09-07 | 09-06 至 09-11 六列；09-06 只属于 09-07 |
| 合成调休 09-12，anchor 09-07 | 09-07 至 09-12 六列 |
| 合成同时调休 09-06 和 09-12 | 明确七列不支持；零创建，零取数，零 AI |
| 跨年 anchor 2026-12-28 | 身份仍为完整日期，不重置周次；实际库不覆盖 2027 时拒绝 |
| 整周假期 | 保留五个日期列、假期掩码，下一周仍递增 |
| 假期跨相邻周 | 每周可见段首日标节名，其余空，不重复日期 |
| 同周缩短选择 / 重复创建 | 同一 root 或冲突，不生成第二份 |
| 同班同周两个学期 / 当前个人设置变更 | 前者明确冲突；后者不改稳定身份 |

合成调休只用于规则单元测试，不宣称这些日期是实际法定调休。真实日历集成另用锁定包的数据验证。
本轮实时查阅官方项目说明：[chinese-calendar](https://github.com/LKI/chinese-calendar)，其声明覆盖
2004–2026；仓库当前未锁定该依赖。WP-D 选择并锁定版本、读实际覆盖范围，不能永久硬编码本次范围。
库包名为 `chinesecalendar`，导入名为 `chinese_calendar`。

## 范围与未决

表名、占用表、错误码是本门技术方案，可通过 Review 收紧；不需要重新询问已确认的产品规则。
本契约将跨学期同周作为显式未支持情况，不猜测选择一方。若未来必须支持同一班同一周拆为两个学期，
需要独立产品决定，当前没有这样做的授权。
