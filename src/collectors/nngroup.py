import logging
import re
from datetime import datetime
from .base import BaseCollector, CollectedItem

logger = logging.getLogger(__name__)


class NNGroupCollector(BaseCollector):
    """NN/g Group (Nielsen Norman Group) AI 用户研究内容采集"""

    name = 'nngroup'
    base_url = 'https://www.nngroup.com/topic/ai/'

    def __init__(self):
        super().__init__()
        # Use base User-Agent

    async def collect(self) -> list[CollectedItem]:
        """采集 NN/g 的 AI 用户研究内容"""
        items = []

        try:
            response = await self.client.get(self.base_url)
            if response.status_code != 200:
                logger.warning(f'{self.name}: HTTP {response.status_code}')
                return items

            html = response.text

            # 解析文章列表 (NN/g 使用 article 或 .article 类)
            # 查找文章链接和标题
            import re

            # 尝试多种选择器
            patterns = [
                r'<article[^>]*>.*?<h[23][^>]*>(.*?)</h[23]>.*?<a[^>]*href="([^"]+)"',
                r'class="article[^"]*"[^>]*>.*?<h[23][^>]*>(.*?)</h[23]>.*?<a[^>]*href="([^"]+)"',
                r'<div[^>]*class="[^"]*article[^"]*"[^>]*>.*?<h[23][^>]*>(.*?)</h[23]>.*?<a[^>]*href="([^"]+)"',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
                if matches:
                    for title, url in matches[:20]:
                        # 清理标题
                        title = re.sub(r'<[^>]+>', '', title).strip()
                        if not url.startswith('http'):
                            url = f'https://www.nngroup.com{url}'

                        items.append(CollectedItem(
                            title=title,
                            summary='',
                            url=url,
                            source=self.name,
                            category='news',
                            published_date=datetime.now().strftime('%Y-%m-%d')
                        ))
                    break

            logger.info(f'{self.name}: 采集到 {len(items)} 条')

        except Exception as e:
            logger.error(f'{self.name}: 采集失败 - {e}')

        return items
