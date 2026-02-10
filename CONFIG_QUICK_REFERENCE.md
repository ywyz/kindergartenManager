# 配置UI快速参考

## 🚀 启动应用

```bash
cd c:\Users\yw980\code\kindergartenManager
python app.py
```

访问: http://localhost:8080

---

## ⚙️ 配置位置

点击页面顶部的 **⚙️ 系统配置** 展开按钮

### 标签页 1: AI配置

| 字段 | 值 | 说明 |
|------|-----|------|
| API Key | `sk-...` | OpenAI API密钥（必填） |
| AI模型 | `gpt-4o-mini` | 使用的AI模型 |
| API地址 | 可选 | 自定义API端点地址 |

**操作**: 填写后点击"保存配置"按钮

### 标签页 2: 数据库配置

**选择数据库类型**:
- ✓ **SQLite (本地)** — 推荐用于本地开发
- ✓ **MySQL (云部署)** — 推荐用于云服务

**MySQL连接参数** (仅在选择MySQL时显示):
| 字段 | 示例 | 说明 |
|------|------|------|
| 数据库地址 | `localhost` | MySQL服务器地址 |
| 端口 | `3306` | MySQL服务器端口 |
| 数据库名 | `kindergarten` | 数据库名称 |
| 用户名 | `root` | MySQL用户 |
| 密码 | `****` | MySQL用户密码 |

**操作**: 选择后自动保存（如需MySQL则需填写参数）

---

## 💾 配置存储

所有配置自动保存到浏览器localStorage中:
- 关闭浏览器后配置仍保留 ✓
- 页面刷新后配置自动恢复 ✓
- 清除浏览器缓存会删除配置 ⚠ 

### localStorage密钥列表

```
kg_manager_ai_key              # API密钥
kg_manager_ai_model            # AI模型
kg_manager_ai_base_url         # 自定义API地址
kg_manager_db_type             # 数据库类型
kg_manager_mysql_*             # MySQL连接参数 (5个)
```

### 清除配置

在浏览器开发者工具中执行:
```javascript
localStorage.clear()  // 清除所有配置
// 或者清除特定项:
localStorage.removeItem('kg_manager_ai_key')
```

---

## 🤖 使用AI功能

1. **在配置中设置AI密钥** ← 重要！
2. 在"集体活动管理原稿"输入框输入内容
3. 点击"分割集体活动"按钮
4. 系统会自动:
   - 检查API密钥
   - 调用OpenAI API
   - 回填各个子字段

**常见问题**:
- ❌ "请先在系统配置中设置 OpenAI API Key" → 在配置中输入密钥
- ❌ "API 处理失败" → 检查网络连接和API密钥有效性
- ❌ "AI 返回格式不正确" → 重试或检查输入内容

---

## 📝 教案操作流程

### 完整流程
```
1. 配置系统 (⚙️ 按钮)
   ↓
2. 输入学期日期
   ↓
3. 填写教案内容 (可用AI辅助)
   ↓
4. 保存到数据库
   ↓
5. 导出为Word文档
```

### 快捷按钮

| 按钮 | 功能 |
|------|------|
| 保存学期 | 记录学期信息 |
| 导出为Word | 生成Word教案文档 |
| 保存到数据库 | 存储教案数据 |
| 分割集体活动 | AI辅助拆分内容 |
| 填充测试数据 | 快速填充示例数据 |
| 清空表单 | 清除所有输入 |
| 加载到表单 | 从数据库加载教案 |
| 连续导出 | 批量生成Word文档 |

---

## 🔍 常见配置场景

### 场景1: 本地开发

```
AI配置:
  API Key: sk-xxxx...
  AI模型: gpt-4o-mini
  API地址: (留空，使用默认)

数据库配置:
  ✓ SQLite (本地)
  文件位置: examples/plan.db
```

### 场景2: 云部署 (MySQL)

```
AI配置:
  API Key: sk-xxxx... (或兼容API)
  AI模型: gpt-4o-mini
  API地址: https://api.example.com/v1

数据库配置:
  ✓ MySQL (云部署)
  地址: mysql.example.com
  端口: 3306
  数据库: kindergarten_prod
  用户: app_user
  密码: secure_password
```

### 场景3: 本地MySQL开发

```
AI配置:
  API Key: sk-xxxx...
  AI模型: gpt-4o-mini
  API地址: (留空)

数据库配置:
  ✓ MySQL (云部署)
  地址: localhost
  端口: 3306
  数据库: kindergarten_dev
  用户: root
  密码: (本地密码)
```

---

## ⚡ 快捷键和技巧

### 键盘操作
- Tab: 在表单字段间切换
- Enter: 提交表单或按钮点击
- Ctrl+A: 全选文本

### 浏览器开发者工具
```javascript
// 查看当前配置
const config = {
  ai_key: localStorage.getItem('kg_manager_ai_key'),
  db_type: localStorage.getItem('kg_manager_db_type'),
  mysql_host: localStorage.getItem('kg_manager_mysql_host'),
  // ...
}
console.log(config)

// 导出配置为JSON
const allConfig = {};
for (let i = 0; i < localStorage.length; i++) {
  const key = localStorage.key(i);
  if (key.startsWith('kg_manager_')) {
    allConfig[key.replace('kg_manager_', '')] = localStorage.getItem(key);
  }
}
console.log(JSON.stringify(allConfig, null, 2))

// 导入配置
const newConfig = { /* 配置对象 */ };
Object.entries(newConfig).forEach(([key, value]) => {
  localStorage.setItem('kg_manager_' + key, value);
});
```

---

## 🆘 故障排查

| 问题 | 排查步骤 |
|------|--------|
| 配置未保存 | 检查localStorage是否启用 (浏览器设置) |
| 页面刷新后配置丢失 | 检查浏览器是否清除了缓存 |
| AI功能无响应 | 检查API密钥有效性，网络连接 |
| 数据库保存失败 | 检查MySQL服务是否运行，连接参数是否正确 |
| UI无法显示 | 刷新页面，清除浏览器缓存，重启应用 |

### 调试模式

查看日志信息 (浏览器控制台):
```
F12 → Console 标签页 → 查看错误消息
```

### 重置应用

```bash
# 清除所有数据库
rm -r examples/plan.db examples/semester.db

# 重新启动
python app.py
```

---

## 📚 相关文件

- 配置使用指南: `CONFIG_UI_GUIDE.md`
- 技术实现细节: `CONFIG_IMPLEMENTATION_SUMMARY.md`
- 本会话总结: `SESSION_SUMMARY.md`
- 应用主文件: `app.py`
- 核心库: `kg_manager/`

---

**版本**: 1.0 (配置UI完整实现版)  
**最后更新**: 2024年12月  
**状态**: ✅ 生产就绪
