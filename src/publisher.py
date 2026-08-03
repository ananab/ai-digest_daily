import logging
import httpx
from datetime import date
from .config import config

logger = logging.getLogger(__name__)


class FeishuPublisher:
    """飞书 Webhook 发布器"""

    def __init__(self):
        self.webhook_url = config.feishu_webhook_url
        self.client = httpx.AsyncClient(timeout=30)

    async def publish(self, report: dict):
        """
        发布报告到飞书

        Args:
            report: 分析报告字典 {'report': '...', 'data': {...}}
        """
        if not self.webhook_url:
            logger.error('飞书 Webhook URL 未配置')
            return False

        # 构建飞书消息卡片
        card = self._build_card(report)

        try:
            # 记录请求内容大小
            report_text = report.get('report', '')
            logger.info(f'报告长度: {len(report_text)} 字符')

            response = await self.client.post(
                self.webhook_url,
                json=card,
            )

            logger.info(f'飞书响应状态码: {response.status_code}')
            logger.info(f'飞书响应内容: {response.text[:500]}')

            response.raise_for_status()

            result = response.json()
            if result.get('code') == 0 or result.get('StatusCode') == 0:
                logger.info('飞书推送成功')
                return True
            else:
                logger.error(f'飞书推送失败: {result}')
                return False

        except httpx.HTTPStatusError as e:
            logger.error(f'飞书HTTP错误: 状态码={e.response.status_code}, 响应={e.response.text[:500]}')
            return False
        except Exception as e:
            logger.error(f'飞书推送异常: {type(e).__name__}: {e}')
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _build_card(self, report: dict) -> dict:
        """构建飞书消息卡片"""
        report_text = report.get('report', '')
        today = date.today().strftime('%Y-%m-%d')

        # 飞书卡片消息格式
        card = {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True
                },
                "header": {
                    "template": "blue",
                    "title": {
                        "content": f"🤖 AI 前沿日报 | {today}",
                        "tag": "plain_text"
                    }
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": report_text
                    },
                    {
                        "tag": "hr"
                    },
                    {
                        "tag": "note",
                        "elements": [
                            {
                                "tag": "plain_text",
                                "content": "由 AI Daily Digest 自动生成 | Powered by Kimi"
                            }
                        ]
                    }
                ]
            }
        }

        return card

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
