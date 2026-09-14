# WP-E 用户参考版式续作 2026-09-12

本轮用户要求按其提供的周计划 DOCX 修改当前测试输出。原件保留，复制为本地 reference-original.docx；文件内容只作参考，不构成新的操作授权或 released 资格。

产品代码冻结 SHA：1b07c6a400b49e5987b484ecb9935acae4b8817e。上轮产品 SHA 908f4a2cd076b5bc08d2373db34a966d7ace7919；其文档后继4f78e354a342ee07e638f138968da55346bbd303。本轮仅隔离 worktree 本地提交，无 push、部署、迁移、凭据操作或 Issue 消息。

参考 SHA256：43dfb11021a76fbda76dc0a0e5c17ec6fdebf5616f9aa21df8632e82534c353e。受控 seed hash 仍为 f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b，原字节未改写。参考文件包含三周实填内容，不能直接作为单周或云端 released 模板记录。

## 修改与有意保留

恢复受控模板与参考共有的16pt加粗居中标题、窄标签列、双层标签换行、底部第一列标签其余整周合并。grid/cell宽度一致且限制在打印宽度内。户外游戏恢复集体/自主分类，区域完整标签与目标/指导逐项换行，本周重点、环境、习惯逐项换行。正文仍宋体12pt、固定20pt。日期五/六列与假期集体活动空白规则保留。

现行spec2.2固定标题仍为“幼儿园每周工作计划表”，没有直接复制参考中的园名或人员；表头保留权威班级/学期/周次、逐日日期。参考的局部较小行距、三周长正文未照抄或自动缩减。当前8份正文仍是原有合成验收输入，未冒充用户真实周计划或云端数据。用户可先查看本地五/六列短文候选确认版式。

## 保全与验证

本地 wp-e-user-reference-20260912 保存 before-shared_weekly_word.py、before-test_wpe_word_layout.py、双RED、生成脚本、候选输入/输出及逐件hash清单。原8份post-fix及pre-fix DOCX、历史ZIP、26份handoff清单均未覆盖。

reference-red1/2 均五/六列2fail，首先失败于标题12pt不等于16pt；不声称每个后续布局断言分别取得RED。独立复审发现标题未恢复加粗，title-bold-red1/2 均五/六列2fail后最小补修。最终所选回归8passed8deselected（Python3.12.14辅助环境，非要求的完整3.14环境）。独立只读复审确认本轮有限源码范围，无剩余发现。实际renderer集成/全回归仍未执行，不从这8项推断通过。

handoff再次运行：INTEGRITY_OK: 26 files; not Word or WP-E PASS。新8份DOCX不在此26份中。candidate-manifest.json绑定当前SHA、renderer源hash、参考hash、seed、原body hash和新输出hash。released_binding仅继承来源声明；当前Ubuntu released事实未验证，不能安装为正式资格。

辅助视觉预检：使用已安装 D:/Program Files/LibreOffice/program/soffice.exe 与bundled render_docx.py。初次PATH查找失败保留日志；包装脚本在子进程内部设定已知PATH后成功。five-normal、six-sunday-normal各一页PNG逐页查看，未见明显重叠、裁切、缺字。仅LO辅助视觉预检，非Word或WP-E PASS；其余6份新候选视觉预检NOT_RUN。

原生Word控制：当前仍定位到上轮five-normal窗口。打开对话框出现索引不可用、type_text超时、focus与可见文件名不一致；重新连接后set_value返回Cannot set a value for an element that is not settable。未确认打开本轮新DOCX，故本轮8格原生Word均NOT_RUN/BLOCKED，不能继承上轮旧文件一页观察。需要恢复可靠可见控制或由用户原生Word打开新文件并提供全部页观察材料。

## 剩余门

Windows Server2025 Datacenter仍按用户授权为可接受环境；上轮Word账户/关于产品build证据只覆盖实际记录，不因Server名称阻塞。新矩阵仍需正常/长中文、多姓名、空格、书名号、数量、日期/假期、换行、全页原生预览、A4、正文宋体12pt固定20pt、标题、实际单页及裁切字体观察与独立复审。

正式catalog、安装输入与目标授权、当前released事实、renderer及新五/六列hash绑定待补。目标Ubuntu页面全分支、真实超页缩减采用保存重检链、exact-SHA CI、不可变OCI、真实模型、凭据、迁移部署证据各自待验。WP-C四类历史native双RED继续UNMET；历史long三份两页FAIL、compact合成候选不变。

WP-E仍BLOCKED，WP-F NOT_RUN；未生成WP-F-next-prompt.md。
