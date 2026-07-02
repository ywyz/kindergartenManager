# @kindergarten/storage

对象存储基础包。

## 当前职责

- 生成稳定对象 key。
- 禁止用户输入作为路径片段直接拼接。
- 限制文件扩展名只保留安全字符。

## 验证

```bash
pnpm --filter @kindergarten/storage typecheck
pnpm test:gate
```
