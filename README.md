# AI 前沿信息每日汇总 Agent

自动化采集多源 AI 领域最新动态，通过 Kimi (Moonshot AI) 智能分析，每日推送到飞书机器人。

## 数据源

- **AI 热点聚合站** (aihot.virxact.com)
- **Hugging Face Daily Papers**
- **Arxiv 最新论文** (cs.AI, cs.CL, cs.CV)
- **GitHub Trending** (AI/ML 项目)
- **Hacker News** (AI 相关热门讨论)
- **Reddit r/MachineLearning**

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填入以下配置：

```bash
KIMI_API_KEY=your_kimi_api_key
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your_webhook_id
```

### 3. 运行

```bash
python src/main.py
```

## CI/CD 自动部署

支持 GitHub Actions 和 GitLab CI 两种部署方式。

### GitHub Actions

项目包含 `.github/workflows/daily-digest.yml`，每天北京时间 9:00 自动运行。

在仓库 Settings → Secrets → Actions 中添加：

- `KIMI_API_KEY`
- `FEISHU_WEBHOOK_URL`

### GitLab CI

项目包含 `.gitlab-ci.yml`。定时任务在 UI 配置：

1. 进入项目 **Settings → CI/CD → Pipeline schedules**
2. 点 **New schedule**，设置 cron: `0 1 * * *`（UTC），时区选 UTC
3. 添加两个 CI/CD Variables（Settings → CI/CD → Variables）：
   - `KIMI_API_KEY`（勾选 Masked）
   - `FEISHU_WEBHOOK_URL`（勾选 Masked）
4. 点 **Run pipeline** 立即测试一次

注意：GitLab 免费额度 400 分钟/月（共享 runner），私有 runner 不限。

## 飞书机器人配置

1. 在目标飞书群聊中，点击「设置」→「群机器人」→「添加机器人」→「自定义机器人」
2. 配置机器人名称（如「AI 前沿日报」）和头像
3. 复制 Webhook URL
4. 添加到 `.env` 或 GitHub Secrets

## 费用

- GitHub Actions: 公开仓库免费
- Kimi API: 每日约 ¥0.1-0.3，每月约 ¥3-9（取决于模型和用量）

## 项目结构

```
ai-daily-digest/
├── .github/workflows/     # GitHub Actions 配置
├── src/
│   ├── collectors/        # 各数据源采集器
│   ├── main.py           # 主入口
│   ├── config.py         # 配置管理
│   ├── processor.py      # 数据处理器
│   ├── analyzer.py       # Kimi API 分析
│   └── publisher.py      # 飞书推送
├── requirements.txt
└── README.md
```
