import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """应用配置"""

    # DeepSeek API (primary)
    deepseek_api_key: str = os.getenv('DEEPSEEK_API_KEY', '')
    deepseek_model: str = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
    deepseek_base_url: str = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')

    # Kimi (Moonshot AI) API (backup)
    kimi_api_key: str = os.getenv('KIMI_API_KEY', '')
    kimi_model_filter: str = os.getenv('KIMI_MODEL_FILTER', 'kimi-k2.7-code')
    kimi_model_report: str = os.getenv('KIMI_MODEL_REPORT', 'kimi-k2.6')

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
        if not self.deepseek_api_key and not self.kimi_api_key:
            raise ValueError('DEEPSEEK_API_KEY 或 KIMI_API_KEY 至少配置一个')
        if not self.feishu_webhook_url:
            raise ValueError('FEISHU_WEBHOOK_URL 未配置')


config = Config()
