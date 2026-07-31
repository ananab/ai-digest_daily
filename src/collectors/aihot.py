import logging
from bs4 import BeautifulSoup
from .base import BaseCollector, CollectedItem

logger = logging.getLogger(__name__)


class AIHotCollector(BaseCollector):
    """aihot.virxact.com 聚合站爬虫"""

    name = 'aihot'

    async def collect(self) -> list[CollectedItem]:
        items = []
        try:
            response = await self.client.get('https://aihot.virxact.com/')
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'lxml')

            # 根据实际页面结构解析，尝试多种常见选择器
            for article in soup.select('article, .item, .card, [class*="post"], [class*="news"]'):
                title_el = article.select_one('h1, h2, h3, .title, a')
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                link = title_el.get('href', '') or ''
                if link and not link.startswith('http'):
                    link = f'https://aihot.virxact.com{link}'

                summary_el = article.select_one('p, .summary, .desc, .description')
                summary = summary_el.get_text(strip=True) if summary_el else ''

                items.append(CollectedItem(
                    title=title,
                    summary=summary,
                    url=link,
                    source='AI热点聚合',
                    category='news',
                ))

            if not items:
                # 回退：尝试解析所有带链接的标题
                for a_tag in soup.select('a[href]'):
                    title = a_tag.get_text(strip=True)
                    if title and len(title) > 8 and len(title) < 200:
                        href = a_tag['href']
                        if not href.startswith('http'):
                            href = f'https://aihot.virxact.com{href}'
                        items.append(CollectedItem(
                            title=title,
                            url=href,
                            source='AI热点聚合',
                            category='news',
                        ))

            logger.info(f'AIHot: 采集到 {len(items)} 条新闻')
        except Exception as e:
            logger.error(f'AIHot 采集失败: {e}')

        return items
