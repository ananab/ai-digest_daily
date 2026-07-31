# GitLab CI 配置指南

## 1. 推送代码到 GitLab

```bash
cd ai-daily-digest

# 初始化 git
git init
git add .
git commit -m "Initial commit: AI Daily Digest"

# 关联你的 GitLab 仓库（替换为你的地址）
git remote add origin https://gitlab.com/your-namespace/ai-daily-digest.git

# 推送
git branch -M main
git push -u origin main
```

## 2. 配置定时任务（Pipeline Schedule）

1. 登录 GitLab，进入你的项目页面
2. 左侧菜单：**Settings → CI/CD → Pipeline schedules**
3. 点击 **New schedule**
4. 填写：
   - **Description**: `AI Daily Digest`
   - **Interval pattern**: `0 22 * * *`（每天 UTC 22:00 = 北京时间 06:00）
   - **Timezone**: 选择 `UTC`
   - **Target branch**: `main`
5. 点击 **Save pipeline schedule**

## 3. 添加 CI/CD Variables（密钥）

1. 左侧菜单：**Settings → CI/CD → Variables**
2. 点击 **Add variable**

### 变量 1: ANTHROPIC_API_KEY
- **Key**: `ANTHROPIC_API_KEY`
- **Value**: 你的 Claude API 密钥（从 https://console.anthropic.com 获取）
- **Type**: Variable
- **Flags**: 
  - ✅ Protect variable（只在 protected 分支可用）
  - ✅ Mask variable（日志中隐藏）
- 点击 **Add variable**

### 变量 2: FEISHU_WEBHOOK_URL
- **Key**: `FEISHU_WEBHOOK_URL`
- **Value**: 你的飞书 Webhook 地址
- **Type**: Variable
- **Flags**:
  - ✅ Protect variable
  - ✅ Mask variable
- 点击 **Add variable**

## 4. 手动测试运行

1. 左侧菜单：**CI/CD → Pipelines**
2. 点击 **Run pipeline**
3. 选择分支 `main`，点击 **Run pipeline**
4. 等待 job 完成，检查日志

## 5. 查看运行结果

- **CI/CD → Jobs**: 查看每次运行的日志
- **CI/CD → Pipelines**: 查看所有 pipeline 状态
- 飞书群聊应该收到消息

## 6. 常见问题

### Q: Pipeline 显示 "stuck" 或 "pending"
- 检查是否配置了 runner：**Settings → CI/CD → Runners**
- 如果用共享 runner，确保项目是 public 或有足够配额
- 私有项目需要配置自己的 runner

### Q: 定时任务没触发
- 检查 timezone 是否设为 UTC（不是北京时间）
- `0 22 * * *` UTC = 北京时间 06:00

### Q: 变量没生效
- 确保勾选了 "Protect variable" 且分支是 protected
- 或者取消 "Protect variable" 让所有分支可用

### Q: 想看实时日志
- 在 job 运行时点击 **CI/CD → Jobs**，点进具体 job 看实时日志

## 7. Runner 配额

- **GitLab.com 共享 runner**: 免费额度 400 分钟/月
- **私有 runner**: 无限制，自己部署

每次运行约 1-2 分钟，每天 1 次 = 每月 ~60 分钟，完全够用。
