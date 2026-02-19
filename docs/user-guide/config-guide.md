# ⚙️ 系统配置完整指南

本指南详细说明如何配置AI和数据库。

---

## 🤖 AI 配置

### 需要的信息

| 字段 | 说明 | 是否必填 | 示例 |
|------|------|--------|------|
| **API Key** | OpenAI API密钥 | ✅ 是 | `sk-proj-...` |
| **AI模型** | 使用的LLM模型 | ⚪ 否 | `gpt-4o-mini` |
| **API地址** | 自定义API端点 | ⚪ 否 | `https://api.openai.com/v1` |

### 配置步骤

1. **获取API Key**
   - 访问 [OpenAI API Keys](https://platform.openai.com/api/keys)
   - 点击 "Create new secret key"
   - 复制生成的密钥

2. **在系统中配置**
   - 打开应用，点击 ⚙️ **系统配置**
   - 切换到 **AI配置** 标签页
   - 粘贴 API Key
   - （可选）修改模型名称
   - 点击 **保存配置**

3. **验证配置**
   - 回到表单
   - 尝试使用 "分割集体活动" 功能
   - 如果成功处理，说明配置正确

### 支持的AI模型

| 模型 | 推荐场景 | 成本 | 速度 |
|------|--------|------|------|
| `gpt-4o` | 需要最佳质量 | 🔴 高 | 🟡 中等 |
| `gpt-4o-mini` | **推荐**（默认） | 🟢 低 | 🟢 快 |
| `gpt-4-turbo` | 兼容性考虑 | 🟡 中 | 🟡 中等 |
| `gpt-3.5-turbo` | 极简成本 | 🟢 最低 | 🟢 最快 |

### 自定义API端点

如果你使用自建或第三方的OpenAI兼容API：

1. 在 **AI配置** 填写自定义API地址，如：
   - `https://api.chatanywhere.com.cn/v1` (ChatAnywhere)
   - `https://api.openai-sb.com/v1` (OpenAI-SB)
   - 或其他兼容接口

2. 其他配置保持不变

3. 点击 **保存配置**

---

## 💾 数据库配置

### SQLite（本地）- 推荐用于开发

**特点**：
- ✅ 无需额外配置
- ✅ 一键启用
- ✅ 文件存储，易于备份
- ❌ 不支持多用户远程访问

**配置步骤**：
1. 打开 ⚙️ **系统配置**
2. 切换到 **数据库配置** 标签页
3. 选择 **SQLite (本地)**
4. 配置自动保存

**数据文件位置**：
- `examples/plan.db` - 教案数据
- `examples/semester.db` - 学期信息

---

### MySQL（云部署）- 推荐用于团队协作

**特点**：
- ✅ 支持多用户远程访问
- ✅ 适合云部署
- ✅ 专业级性能
- ❌ 需要配置MySQL服务器

**配置步骤**：

1. 确保 MySQL 服务已运行
   ```bash
   # Windows (如果安装了MySQL)
   mysql -u root -p
   
   # macOS
   brew services start mysql
   
   # Linux
   sudo systemctl start mysql
   ```

2. 打开 ⚙️ **系统配置**

3. 切换到 **数据库配置** 标签页

4. 选择 **MySQL (云部署)**

5. 填写以下信息：

   | 字段 | 说明 | 示例 |
   |------|------|------|
   | **数据库地址** | MySQL服务器地址 | `localhost` 或 `mysql.example.com` |
   | **端口** | MySQL服务器端口 | `3306` |
   | **数据库名** | 数据库名称 | `kindergarten_db` |
   | **用户名** | MySQL用户 | `root` 或 `app_user` |
   | **密码** | MySQL用户密码 | `****` |

6. 点击 **保存配置**

**创建数据库（首次使用）**：
```sql
-- 在MySQL中执行以下命令
CREATE DATABASE kindergarten_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- 系统会自动创建所需的表
```

---

## 🔄 配置持久化

所有配置自动保存到浏览器的 `localStorage` 中：

**自动保存的配置**：
```
kg_manager_ai_key              # API密钥
kg_manager_ai_model            # AI模型
kg_manager_ai_base_url         # 自定义API地址
kg_manager_db_type             # 数据库类型（sqlite/mysql）
kg_manager_mysql_host          # MySQL主机
kg_manager_mysql_port          # MySQL端口
kg_manager_mysql_db            # MySQL数据库名
kg_manager_mysql_user          # MySQL用户名
kg_manager_mysql_password      # MySQL密码
```

**特点**：
- ✅ 跨会话保留（关闭浏览器后仍保存）
- ✅ 自动恢复（页面刷新时自动加载）
- ⚠️ 清除浏览器缓存会删除配置

---

## 🔧 配置管理

### 查看当前配置

在浏览器开发者工具中执行：
```javascript
// 按F12打开开发者工具，进入Console标签页，执行：
for (let i = 0; i < localStorage.length; i++) {
  const key = localStorage.key(i);
  if (key.startsWith('kg_manager_')) {
    console.log(key, '=', localStorage.getItem(key));
  }
}
```

### 导出配置（备份）

```javascript
const config = {};
for (let i = 0; i < localStorage.length; i++) {
  const key = localStorage.key(i);
  if (key.startsWith('kg_manager_')) {
    config[key] = localStorage.getItem(key);
  }
}
console.log(JSON.stringify(config, null, 2));
// 复制输出内容保存为 backup.json
```

### 导入配置（恢复）

```javascript
const config = {
  "kg_manager_ai_key": "sk-...",
  "kg_manager_db_type": "sqlite",
  // ... 其他配置
};
Object.entries(config).forEach(([key, value]) => {
  localStorage.setItem(key, value);
});
console.log('✓ 配置恢复成功');
```

### 清除特定配置

```javascript
// 清除所有配置
localStorage.clear();

// 只清除AI配置
localStorage.removeItem('kg_manager_ai_key');
localStorage.removeItem('kg_manager_ai_model');
localStorage.removeItem('kg_manager_ai_base_url');

// 只清除MySQL配置
['host', 'port', 'db', 'user', 'password'].forEach(key => {
  localStorage.removeItem(`kg_manager_mysql_${key}`);
});
```

---

## 🐛 故障排查

### 问题：配置未保存

**检查步骤**：
1. 确认点击了 **保存配置** 按钮
2. 检查浏览器是否启用了localStorage
   - Firefox: 菜单 → 设置 → 隐私 → Cookies 和站点数据（启用）
   - Chrome: 设置 → 隐私和安全 → Cookie和其他网站数据（启用）
3. 如果使用无痕/隐私浏览模式，localStorage会在关闭后删除

### 问题：AI功能无响应

**检查步骤**：
1. 确认API Key正确：访问 [OpenAI API Keys](https://platform.openai.com/api/keys) 重新复制
2. 检查网络连接，尝试ping `api.openai.com`
3. 检查API额度是否足够：[Billing Overview](https://platform.openai.com/billing/overview)
4. 查看浏览器控制台（F12）的错误消息

**常见错误**：
- `401 Unauthorized` - API Key错误或过期
- `429 Too Many Requests` - 请求过于频繁，请稍候
- `500 Server Error` - OpenAI服务器错误，请稍后重试

### 问题：MySQL连接失败

**检查步骤**：
1. 确认MySQL服务已启动
2. 验证连接参数：
   ```bash
   mysql -h <host> -P <port> -u <user> -p
   # 输入密码，如能连接说明参数正确
   ```
3. 确认数据库已创建：
   ```sql
   SHOW DATABASES;  -- 应该能看到 kindergarten_db
   ```
4. 检查用户权限：
   ```sql
   GRANT ALL PRIVILEGES ON kindergarten_db.* TO '<user>'@'<host>';
   FLUSH PRIVILEGES;
   ```

---

## 📚 相关文档

→ [快速开始](quickstart.md) - 5分钟快速上手  
→ [AI功能使用](../ai-integration/user-guide.md) - 如何使用AI拆分功能  
→ [常见问题](../reference/faq.md) - 更多问题解答
