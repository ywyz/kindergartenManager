# @kindergarten/worker

dev4.0 后台任务服务入口。

## 当前职责

- 保留 worker 进程边界。
- 后续承载 AI 生成、Word 导出、Excel 处理、备份和恢复任务。

## 验证

```bash
pnpm --filter @kindergarten/worker typecheck
```
