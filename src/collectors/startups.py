import logging
import feedparser
from bs4 import BeautifulSoup
from .base import BaseCollector, CollectedItem

logger = logging.getLogger(__name__)


class StartupsCollector(BaseCollector):
    """Startups新闻采集 - TechCrunch AI, Newcomer, ProductHunt"""

    name = 'startups'

    async def collect(self) -> list[CollectedItem]:
        items = []

        feeds = [
            ('https://techcrunch.com/category/artificial-intelligence/feed/', 'TechCrunch AI'),
            ('https://www.newcomer.co/feed', 'Newcomer'),
            ('https://www.producthunt.com/feed', 'ProductHunt'),
        ]

        for feed_url, source in feeds:
            try:
                response = await self.client.get(feed_url)
                response.raise_for_status()
                feed = feedparser.parse(response.text)

                for entry in feed.entries[:15]:
                    title = entry.get('title', '')
                    link = entry.get('link', '')
                    summary = entry.get('summary', '')
                    summary = BeautifulSoup(summary, 'lxml').get_text(strip=True)
                    if len(summary) > 300:
                        summary = summary[:300] + '...'

                    items.append(CollectedItem(
                        title=title,
                        summary=summary,
                        url=link,
                        source=source,
                        category='startups',
                    ))

                logger.info(f'{source}: 采集到 {len(feed.entries)} 条')

            except Exception as e:
                logger.error(f'{source} 采集失败: {e}')

        return items
