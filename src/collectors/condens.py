import logging
import re
from datetime import datetime
from .base import BaseCollector, CollectedItem

logger = logging.getLogger(__name__)


class CondensCollector(BaseCollector):
    """Condens 用户研究平台博客采集"""

    name = 'condens'
    base_url = 'https://condens.io/blog'

    def __init__(self):
        super().__init__()
        # Use base User-Agent

    async def collect(self) -> list[CollectedItem]:
        """采集 Condens 博客内容"""
        items = []

        try:
            response = await self.client.get(self.base_url)
            if response.status_code != 200:
                logger.warning(f'{self.name}: HTTP {response.status_code}')
                return items

            html = response.text

            # 解析文章列表
            patterns = [
                r'<article[^>]*>.*?<h[23][^>]*>(.*?)</h[23]>.*?<a[^>]*href="([^"]+)"',
                r'class="blog[^"]*"[^>]*>.*?<h[23][^>]*>(.*?)</h[23]>.*?<a[^>]*href="([^"]+)"',
                r'<a[^>]*href="([^"]+)"[^>]*>\s*<h[23][^>]*>(.*?)</h[23]>',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
                if matches:
                    for match in matches[:20]:
                        if len(match) == 2:
                            if match[0].startswith('http'):
                                url, title = match
                            else:
                                title, url = match
                        else:
                            continue

                        title = re.sub(r'<[^>]+>', '', title).strip()
                        if not url.startswith('http'):
                            url = f'https://condens.io{url}'

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
