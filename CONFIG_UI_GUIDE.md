# 配置UI使用指南

## 概述

应用程序现已包含完整的配置管理界面，用户可以在此配置AI设置和数据库连接参数。所有配置都保存在浏览器的localStorage中，以实现跨会话的持久化。

## 功能特性

### 1. AI配置选项卡

**位置**: 页面顶部"⚙️ 系统配置"展开区域 → "AI配置"选项卡

**可配置项**:
- **API密钥** (必填): OpenAI API密钥
- **模型名称** (可选): 默认为 `gpt-4o-mini`
- **自定义API地址** (可选): 用于自定义OpenAI兼容的API端点

**功能**:
- 输入配置后点击"保存配置"按钮即可保存到localStorage
- 页面刷新后配置会自动恢复
- AI分割功能会自动检查API密钥是否已配置

### 2. 数据库配置选项卡

**位置**: 页面顶部"⚙️ 系统配置"展开区域 → "数据库配置"选项卡

**数据库类型选择**:
- **SQLite (本地)**: 使用本地数据库文件 `examples/plan.db`
  - 无需额外配置
  - 适合单机使用

- **MySQL (云部署)**: 使用远程MySQL数据库
  - 需配置以下参数:
    - **数据库地址**: MySQL服务器主机地址 (如 `localhost` 或 `192.168.1.100`)
    - **端口**: MySQL服务器端口 (默认 `3306`)
    - **数据库名称**: 教案数据库名称
    - **用户名**: MySQL连接用户名
    - **密码**: MySQL连接密码

**功能**:
- 选择数据库類型时，MySQL配置字段会动态显示/隐藏
- 所有配置保存到localStorage，即使关闭浏览器也会保留
- 教案数据会根据选择的数据库类型自动保存到相应位置

## localStorage存储

所有配置存储在浏览器localStorage中，使用以下键:

```
kg_manager_ai_key           # AI API密钥
kg_manager_ai_model         # AI模型名称
kg_manager_ai_base_url      # AI自定义API地址
kg_manager_db_type          # 数据库类型 (sqlite/mysql)
kg_manager_mysql_host       # MySQL主机
kg_manager_mysql_port       # MySQL端口
kg_manager_mysql_db         # MySQL数据库名
kg_manager_mysql_user       # MySQL用户名
kg_manager_mysql_password   # MySQL密码
```

## 工作流程

1. **首次使用**: 
   - 打开应用程序 → 点击展开"⚙️ 系统配置"
   - 在AI配置中输入您的OpenAI API密钥
   - 选择数据库类型（推荐MySQL用于云部署，SQLite用于本地）
   - 如选择MySQL，填入所有连接参数
   - 点击保存按钮

2. **后续使用**:
   - 配置会自动加载，无需重复输入
   - 可随时在配置面板中修改任何参数
   - 修改后点击保存按钮更新localStorage

3. **使用AI分割功能**:
   - 在AI配置中确保API密钥不为空
   - 点击"分割集体活动"按钮
   - 应用程序会使用保存的API密钥和模型
   - 分割结果直接填充到表单中

4. **保存教案**:
   - 点击"保存到数据库"按钮
   - 教案会保存到所选的数据库类型中
   - 可在"数据库教案"部分查看和加载已保存的教案

## 注意事项

- **API密钥安全**: 虽然密钥存储在本地的localStorage中，建议定期更换密钥
- **MySQL连接**: 确保MySQL服务器可访问，否则保存操作会失败
- **浏览器兼容性**: 某些浏览器可能禁用localStorage，请检查浏览器设置
- **默认配置**: 首次使用时数据库默认选择MySQL，可根据需要改为SQLite

## 故障排查

| 问题 | 解决方案 |
|------|--------|
| 无法保存配置 | 检查浏览器localStorage是否启用 |
| AI分割失败 | 确认API密钥有效，检查网络连接 |
| 教案保存失败 | 检查MySQL连接参数，确保服务器可访问 |
| 配置丢失 | 清除浏览器缓存可能导致localStorage丢失，建议导出配置备份 |
