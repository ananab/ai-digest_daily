import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """应用配置"""

    # Claude API
    anthropic_api_key: str = os.getenv('ANTHROPIC_API_KEY', '')
    claude_model_filter: str = os.getenv('CLAUDE_MODEL_FILTER', 'claude-3-5-haiku-20241022')
    claude_model_report: str = os.getenv('CLAUDE_MODEL_REPORT', 'claude-3-5-sonnet-20241022')

    # 飞书
    feishu_webhook_url: str = os.getenv('FEISHU_WEBHOOK_URL', '')

    # 数量限制
    max_news_items: int = int(os.getenv('MAX_NEWS_ITEMS', '20'))
    max_papers: int = int(os.getenv('MAX_PAPERS', '10'))
    max_repos: int = int(os.getenv('MAX_REPOS', '10'))

    # 请求配置
    request_timeout: int = 30
    user_agent: str = 'Mozilla/5.0 (compatible; AI-Daily-Digest/1.0)'

    def validate(self):
        """验证必需配置"""
        if not self.anthropic_api_key:
            raise ValueError('ANTHROPIC_API_KEY 未配置')
        if not self.feishu_webhook_url:
            raise ValueError('FEISHU_WEBHOOK_URL 未配置')


config = Config()
