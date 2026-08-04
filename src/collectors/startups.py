import logging
import feedparser
from bs4 import BeautifulSoup
from .base import BaseCollector, CollectedItem

logger = logging.getLogger(__name__)


class StartupsCollector(BaseCollector):
    """Startups新闻采集 - TechCrunch AI, Newcomer, ProductHunt"""

    name = 'startups'

    # ProductHunt 过滤关键词（标题或摘要必须包含至少一个）
    PH_KEYWORDS = [
        'ai', 'gpt', 'llm', 'agent', 'chatbot', 'copilot',
        'machine learning', 'startup', 'launch', 'funding',
        'saas', 'automation', 'assistant', 'generator',
    ]

    async def collect(self) -> list[CollectedItem]:
        items = []

        feeds = [
            ('https://techcrunch.com/category/artificial-intelligence/feed/', 'TechCrunch AI', False),
            ('https://www.newcomer.co/feed', 'Newcomer', False),
            ('https://www.producthunt.com/feed', 'ProductHunt', True),  # 需要关键词过滤
        ]

        for feed_url, source, needs_filter in feeds:
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

                    # ProductHunt 需要关键词过滤
                    if needs_filter:
                        text = (title + ' ' + summary).lower()
                        if not any(kw in text for kw in self.PH_KEYWORDS):
                            continue

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
