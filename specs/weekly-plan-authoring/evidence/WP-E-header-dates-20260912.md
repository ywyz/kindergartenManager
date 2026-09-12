# WP-E 表头日期位置续作 2026-09-12

用户明确要求：班级后跟当前周具体时间，星期下不加日期，左上角空、不填周次。现行spec2.7已记该确认。仅调整导出显示；页面权威班级/学期/周次与日历业务未改。

产品SHA acf9b19bf2f7a84a0c2b4476bbeacfb520bc7780；前产品1b07c6a400b49e5987b484ecb9935acae4b8817e，前文档c4e355eb1d62894009222b51dba0ed6a74c11dc5。班级后用日历列首末日完整年月日；顶行只星期，左上合并格留空。

保全与测试：本地wp-e-header-dates-20260912保留旧renderer/test及日志。最初red1.log/red2.log/green.log因测试fixture错误replace(days)失败，不计业务RED。修正base.days后，对保全旧renderer运行business-red1/2均4fail，实际失败于日期范围展示；新renderer为12passed8deselected。含五/六列跨月、跨年，合成日历不证明真实假期。独立只读复审无新增问题。Python3.12.14辅助环境，不是完整3.14及实际renderer集成回归。

8份新DOCX、body、candidate-manifest.json另目录保存，绑定新SHA、renderer hash、seed hash、来源和每件输出hash。正式seed原字节不改；released仍仅来源声明，Ubuntu当前released未验证。此前各批原始DOCX、原参考和清单未覆盖。

辅助预览用已安装LibreOffice及bundled render_docx.py；five-normal、six-sunday-normal各一页，逐页PNG检查：班级后日期完整，星期下无日期，左上角空白，无明显裁切或重叠。仅辅助视觉预检；其余6份未作本轮视觉验收。本轮未重新进行原生Word操作，8份原生资格均NOT_RUN，既往原生控制阻塞仍待恢复或用户提供全页材料。

handoff仍INTEGRITY_OK: 26 files; not Word or WP-E PASS。26份不包含新DOCX。Word全矩阵、正式catalog/安装授权、Ubuntu全分支、真实超页缩减保存重检、exact-SHA CI、OCI、模型及部署各门未因此关闭。历史WP-C四类native双RED UNMET，历史long两页FAIL及compact合成候选不改。WP-E BLOCKED；WP-F NOT_RUN，未生成WP-F-next-prompt.md。
