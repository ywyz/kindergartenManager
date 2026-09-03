# 模板中心稳定 RED 说明

本目录只穿过模板中心未来的公开 `app.service.template_center` seam，测试不导入尚不存在的生产模块到
collection 阶段；各测试在用例内部延迟导入，以保持 collection clean。测试使用确定性的内存 blob/version/
transaction/audit/policy/export/backup ports 和合成 OOXML bytes，不读取真实模板、数据库、真实凭据或网络，不使用
`sleep`、`skip`、`xfail`、源码文本匹配或生产私有字段。

## 文件与矩阵

| 文件 | 行为矩阵 |
|---|---|
| `test_template_center_registry_red.py` | global known 七类、phase1 enabled 五类、周/月 disabled 拒绝、不可变版本摘要、权限投影和 tenant scope |
| `test_template_center_upload_red.py` | `.docx`/ZIP/XML/宏/外链/路径/压缩炸弹/占位符校验、hash/size、重复 hash 新版本、staged 失败原子性 |
| `test_template_center_lifecycle_red.py` | validation 与 active pointer 分离、validated 重复 active、CAS/stale/跨租户拒绝、active 唯一、blob 不删除、审计 |
| `test_template_center_preview_export_red.py` | synthetic-only preview、零持久化、resolve/render/parse 版本证据、无 active 不 fallback |
| `test_template_center_backup_red.py` | manifest 闭合、owner-only/隔离 staging、篡改/未知成员/权限/路径/tenant/hash 失败和原子恢复 |
| `test_template_center_candidate_qualification_red.py` | T011 受控周/月 seed/fixture qualification、前置拒绝与安全阶段 macro/external-rel/bad-ZIP/structure-profile mismatch、Office failed/缺 Word/缺 LibreOffice/缺 evidence ID/精确版本、同一 opaque export port render/parse、无 public CRUD/active/正式 Preview |

测试对应的最小公开对象和方法在 [`../spec.md`](../spec.md) §3.3、§3.7、§3.10、§3.11 中冻结；T011 内部候选资格
窄 seam 在 §3.12 冻结。候选资格测试不把内部 job 当作 `TemplateCenter` 公共 API。端口的 fake 只记录可观察调用和
效果；测试不得通过 `_private` 属性推断实现。

## RED 门禁

```bash
.venv/bin/python -m pytest specs/template-center/tests --collect-only -q
.venv/bin/python -m pytest specs/template-center/tests -q --tb=no
.venv/bin/python -m pytest specs/template-center/tests -q --tb=no
```

必须满足：

1. collection 成功且无 collection error；
2. 连续两次 collected/passed/failed 和失败 node ID 完全相同；
3. 失败只指向缺失/未满足的 `app.service.template_center` 正式 seam；
4. 无 skip/xfail、固定长 sleep、真实网络/凭据、模板工作树写入或生产迁移；
5. 这些测试不替代 Issue #55 权限矩阵、模板契约 ADR、周/月独立 spec/RED、T011 candidate qualification evidence 或当前五类 Word 人工验收。

完成 RED 后先做双轴 Review；只有 Review 0/0、明确 GREEN 授权且 T001/T002 已接受，才按 spec §6 的
T003–T011 顺序实现。当前目录的 RED 结果不构成 GREEN、合并、发布或 Issue 关闭证据。

## 2026-09-02 本地 RED 证据

在正式生产模块尚未创建的当前工作树执行：

```text
.venv/bin/python -m pytest specs/template-center/tests --collect-only -q
49 tests collected

.venv/bin/python -m pytest specs/template-center/tests -q --tb=no
49 failed in 0.11s

.venv/bin/python -m pytest specs/template-center/tests -q --tb=no
49 failed in 0.11s
```

两次失败 node ID 完全一致；`--tb=short -x` 的首个异常为
`ModuleNotFoundError: No module named 'app.service.template_center'`。无 skip、xfail 或 collection error。
这是缺失正式 seam 的预期 RED，不是生产实现或 GREEN 授权。
